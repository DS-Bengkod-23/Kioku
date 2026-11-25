import uuid
from datetime import datetime, timedelta, timezone

import pytest

from app.config import settings
from app.models.recording import ProcessingStatus
from app.models.recording_session import RecordingSession
from app.services import recording_session as session_service


def _base(meeting_id) -> str:
    return f"/api/v1/meetings/{meeting_id}/recording/sessions"


def _start(client, headers, meeting_id, mime_type: str = "audio/webm"):
    return client.post(_base(meeting_id), headers=headers, json={"mime_type": mime_type})


def _put(client, headers, meeting_id, session_id, index: int, data: bytes = b"audio-bytes"):
    return client.put(
        f"{_base(meeting_id)}/{session_id}/chunks/{index}",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=data,
    )


def _status(client, headers, meeting_id, session_id):
    return client.get(f"{_base(meeting_id)}/{session_id}", headers=headers)


@pytest.fixture
def organizer_meeting(make_user, make_meeting):
    organizer = make_user()
    return organizer, make_meeting(organizer)


@pytest.fixture
def started(client, organizer_meeting, auth_headers, fake_storage):
    """Sesi yang sudah dimulai: (organizer, meeting, headers, session_id)."""
    organizer, meeting = organizer_meeting
    headers = auth_headers(organizer)
    response = _start(client, headers, meeting.id)
    assert response.status_code == 201
    return organizer, meeting, headers, response.json()["session_id"]


# ---------------------------------------------------------------- mulai sesi


def test_start_creates_a_recording_session(client, db_session, organizer_meeting, auth_headers, fake_storage):
    organizer, meeting = organizer_meeting

    response = _start(client, auth_headers(organizer), meeting.id, "audio/webm;codecs=opus")

    assert response.status_code == 201
    body = response.json()
    assert body["status"] == "recording"
    session = db_session.get(RecordingSession, uuid.UUID(body["session_id"]))
    assert session.meeting_id == meeting.id
    assert session.user_id == organizer.id
    assert session.status == "recording"
    assert session.mime_type == "audio/webm"  # parameter codec dibuang
    assert session.chunk_count == 0


@pytest.mark.parametrize(
    "mime_type",
    ["audio/webm", "audio/webm;codecs=opus", "audio/ogg;codecs=opus", "audio/mp4", "Audio/WebM"],
)
def test_start_accepts_browser_audio_types(client, organizer_meeting, auth_headers, fake_storage, mime_type):
    organizer, meeting = organizer_meeting

    assert _start(client, auth_headers(organizer), meeting.id, mime_type).status_code == 201


@pytest.mark.parametrize("mime_type", ["audio/mpeg", "audio/wav", "video/mp4", "text/plain", ""])
def test_start_rejects_unsupported_audio_types(client, organizer_meeting, auth_headers, mime_type):
    organizer, meeting = organizer_meeting

    response = _start(client, auth_headers(organizer), meeting.id, mime_type)

    assert response.status_code == 400
    assert isinstance(response.json()["detail"], str)


def test_start_by_participant_who_is_not_organizer_is_forbidden(
    client, make_user, make_meeting, auth_headers
):
    organizer, member = make_user(), make_user()
    meeting = make_meeting(organizer, members=[member])

    assert _start(client, auth_headers(member), meeting.id).status_code == 403


def test_start_by_stranger_is_forbidden(client, make_user, make_meeting, auth_headers):
    meeting = make_meeting(make_user())

    assert _start(client, auth_headers(make_user()), meeting.id).status_code == 403


def test_start_for_unknown_meeting_is_404(client, make_user, auth_headers):
    assert _start(client, auth_headers(make_user()), uuid.uuid4()).status_code == 404


def test_start_for_soft_deleted_meeting_is_404(client, db_session, organizer_meeting, auth_headers):
    organizer, meeting = organizer_meeting
    meeting.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    assert _start(client, auth_headers(organizer), meeting.id).status_code == 404


def test_start_is_rejected_while_previous_recording_is_still_processed(
    client, db_session, organizer_meeting, auth_headers
):
    organizer, meeting = organizer_meeting
    from app.models.recording import Recording

    db_session.add(
        Recording(meeting_id=meeting.id, file_url="x.m4a", size=1, processing_status=ProcessingStatus.transcribing)
    )
    db_session.commit()

    response = _start(client, auth_headers(organizer), meeting.id)

    assert response.status_code == 409
    # pesan yang sama dengan upload manual
    assert response.json()["detail"].startswith("Rekaman sebelumnya masih diproses AI (status: transcribing)")


def test_start_is_allowed_to_replace_a_finished_recording(client, make_user, make_meeting, auth_headers, fake_storage):
    organizer = make_user()
    meeting = make_meeting(organizer, with_recording=True)  # status completed

    assert _start(client, auth_headers(organizer), meeting.id).status_code == 201


def test_second_active_session_is_409_and_reports_the_existing_one(client, started, auth_headers):
    organizer, meeting, headers, session_id = started
    _put(client, headers, meeting.id, session_id, 0)
    _put(client, headers, meeting.id, session_id, 1)

    response = _start(client, headers, meeting.id)

    assert response.status_code == 409
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["session_id"] == session_id
    assert body["chunk_count"] == 2


def test_losing_a_simultaneous_start_still_reports_the_winner(client, started, monkeypatch):
    # Dua tab memulai bersamaan: pemeriksaan di kode lolos, tapi indeks unik database
    # menolak insert kedua. Hasilnya harus sama dengan 409 sesi aktif, bukan 409 generik.
    organizer, meeting, headers, session_id = started
    real_find = session_service._find_active_session
    calls = []

    def blind_on_first_call(db, meeting_id):
        calls.append(1)
        return None if len(calls) == 1 else real_find(db, meeting_id)

    monkeypatch.setattr(session_service, "_find_active_session", blind_on_first_call)

    response = _start(client, headers, meeting.id)

    assert response.status_code == 409
    assert response.json()["session_id"] == session_id


@pytest.mark.parametrize("finished_status", ["failed", "finalized", "abandoned"])
def test_new_session_is_allowed_after_previous_one_ended(
    client, db_session, started, finished_status
):
    organizer, meeting, headers, session_id = started
    session = db_session.get(RecordingSession, uuid.UUID(session_id))
    session.status = finished_status
    db_session.commit()

    response = _start(client, headers, meeting.id)

    assert response.status_code == 201
    assert response.json()["session_id"] != session_id


# -------------------------------------------------------------- kirim potongan


def test_put_chunk_returns_stored_chunk_count(client, started):
    organizer, meeting, headers, session_id = started

    first = _put(client, headers, meeting.id, session_id, 0, b"aaa")
    second = _put(client, headers, meeting.id, session_id, 1, b"bbb")

    assert first.status_code == 200 and first.json() == {"chunk_count": 1}
    assert second.status_code == 200 and second.json() == {"chunk_count": 2}


def test_put_same_index_again_overwrites_and_does_not_add_a_chunk(client, started, fake_storage):
    organizer, meeting, headers, session_id = started
    _put(client, headers, meeting.id, session_id, 0, b"first-try")

    response = _put(client, headers, meeting.id, session_id, 0, b"second-try")

    assert response.json() == {"chunk_count": 1}
    assert list(fake_storage.objects.values()) == [b"second-try"]


def test_chunks_may_arrive_out_of_order(client, started):
    organizer, meeting, headers, session_id = started

    _put(client, headers, meeting.id, session_id, 1)
    response = _put(client, headers, meeting.id, session_id, 0)

    assert response.json() == {"chunk_count": 2}


def test_put_chunk_updates_session_progress_and_last_activity(client, db_session, started):
    organizer, meeting, headers, session_id = started
    session = db_session.get(RecordingSession, uuid.UUID(session_id))
    long_ago = datetime.now(timezone.utc) - timedelta(minutes=30)
    session.last_activity_at = long_ago
    db_session.commit()

    _put(client, headers, meeting.id, session_id, 0)

    db_session.expire_all()
    session = db_session.get(RecordingSession, uuid.UUID(session_id))
    assert session.chunk_count == 1
    assert session.last_activity_at > long_ago + timedelta(minutes=29)


def test_empty_chunk_is_400(client, started, fake_storage):
    organizer, meeting, headers, session_id = started

    response = _put(client, headers, meeting.id, session_id, 0, b"")

    assert response.status_code == 400
    assert fake_storage.objects == {}


def test_chunk_index_outside_duration_limit_is_400(client, started, monkeypatch):
    # 1 jam / 1800 dtk = 2 potongan, toleransi 50% -> 3 potongan: indeks 0..2 sah.
    monkeypatch.setattr(settings, "MAX_AUDIO_DURATION_HOURS", 1)
    monkeypatch.setattr(settings, "RECORDING_CHUNK_SECONDS", 1800)
    monkeypatch.setattr(settings, "RECORDING_CHUNK_COUNT_TOLERANCE_PERCENT", 50)
    organizer, meeting, headers, session_id = started

    assert _put(client, headers, meeting.id, session_id, 2).status_code == 200
    assert _put(client, headers, meeting.id, session_id, 3).status_code == 400
    assert _put(client, headers, meeting.id, session_id, -1).status_code == 400


def test_chunk_over_size_limit_is_413_and_not_stored(client, started, monkeypatch, fake_storage):
    monkeypatch.setattr(settings, "RECORDING_CHUNK_MAX_SIZE_MB", 1)
    organizer, meeting, headers, session_id = started

    ok = _put(client, headers, meeting.id, session_id, 0, b"x" * (1024 * 1024))
    too_big = _put(client, headers, meeting.id, session_id, 1, b"x" * (1024 * 1024 + 1))

    assert ok.status_code == 200
    assert too_big.status_code == 413
    assert len(fake_storage.objects) == 1


def test_total_over_upload_limit_is_413_and_not_stored(client, started, monkeypatch, fake_storage):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    monkeypatch.setattr(settings, "RECORDING_CHUNK_MAX_SIZE_MB", 1)
    organizer, meeting, headers, session_id = started
    sixty_percent = b"x" * int(1024 * 1024 * 0.6)

    assert _put(client, headers, meeting.id, session_id, 0, sixty_percent).status_code == 200
    response = _put(client, headers, meeting.id, session_id, 1, sixty_percent)

    assert response.status_code == 413
    assert len(fake_storage.objects) == 1


def test_overwriting_a_chunk_counts_only_its_new_size_toward_the_total(
    client, started, monkeypatch, fake_storage
):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 1)
    monkeypatch.setattr(settings, "RECORDING_CHUNK_MAX_SIZE_MB", 1)
    organizer, meeting, headers, session_id = started
    _put(client, headers, meeting.id, session_id, 0, b"x" * int(1024 * 1024 * 0.6))

    # 0,9 MB di indeks yang sama: kalau ukuran lama ikut dihitung, totalnya 1,5 MB.
    response = _put(client, headers, meeting.id, session_id, 0, b"y" * int(1024 * 1024 * 0.9))

    assert response.status_code == 200
    assert response.json() == {"chunk_count": 1}


@pytest.mark.parametrize("ended_status", ["finalizing", "finalized", "failed", "abandoned"])
def test_put_chunk_to_a_session_that_is_not_recording_is_409(client, db_session, started, ended_status):
    organizer, meeting, headers, session_id = started
    session = db_session.get(RecordingSession, uuid.UUID(session_id))
    session.status = ended_status
    db_session.commit()

    assert _put(client, headers, meeting.id, session_id, 0).status_code == 409


def test_put_chunk_by_non_organizer_is_forbidden(client, make_user, make_meeting, auth_headers, fake_storage):
    organizer, member = make_user(), make_user()
    meeting = make_meeting(organizer, members=[member])
    session_id = _start(client, auth_headers(organizer), meeting.id).json()["session_id"]

    assert _put(client, auth_headers(member), meeting.id, session_id, 0).status_code == 403


def test_session_is_not_reachable_through_another_meeting(
    client, make_user, make_meeting, auth_headers, fake_storage
):
    organizer = make_user()
    meeting_a, meeting_b = make_meeting(organizer), make_meeting(organizer)
    headers = auth_headers(organizer)
    session_id = _start(client, headers, meeting_a.id).json()["session_id"]

    assert _put(client, headers, meeting_b.id, session_id, 0).status_code == 404
    assert _status(client, headers, meeting_b.id, session_id).status_code == 404


def test_unknown_session_is_404(client, organizer_meeting, auth_headers):
    organizer, meeting = organizer_meeting
    headers = auth_headers(organizer)

    assert _put(client, headers, meeting.id, uuid.uuid4(), 0).status_code == 404
    assert _status(client, headers, meeting.id, uuid.uuid4()).status_code == 404


# --------------------------------------------------------------- status sesi


def test_status_reports_progress(client, started):
    organizer, meeting, headers, session_id = started
    _put(client, headers, meeting.id, session_id, 0)

    response = _status(client, headers, meeting.id, session_id)

    assert response.status_code == 200
    assert response.json() == {
        "session_id": session_id,
        "status": "recording",
        "chunk_count": 1,
        "error_message": None,
    }


def test_status_reports_failure_reason(client, db_session, started):
    organizer, meeting, headers, session_id = started
    session = db_session.get(RecordingSession, uuid.UUID(session_id))
    session.status = "failed"
    session.error_message = "Konversi audio gagal."
    db_session.commit()

    body = _status(client, headers, meeting.id, session_id).json()

    assert body["status"] == "failed"
    assert body["error_message"] == "Konversi audio gagal."


def test_status_by_non_organizer_is_forbidden(client, make_user, make_meeting, auth_headers, fake_storage):
    organizer, member = make_user(), make_user()
    meeting = make_meeting(organizer, members=[member])
    session_id = _start(client, auth_headers(organizer), meeting.id).json()["session_id"]

    assert _status(client, auth_headers(member), meeting.id, session_id).status_code == 403
