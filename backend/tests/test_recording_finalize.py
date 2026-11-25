import uuid
from pathlib import Path

import pytest

from app.config import settings
from app.models.action_item import ActionItem
from app.models.meeting import Meeting, NotulenStatus
from app.models.recording import ProcessingStatus, Recording
from app.models.recording_session import RecordingSession
from app.models.summary import Summary
from app.models.transcript import Transcript
from app.services.audio_convert import AudioConversionError
from app.tasks.recording_session import finalize_recording_session_task

TINY_M4A = Path(__file__).resolve().parent / "fixtures" / "tiny.m4a"


def _base(meeting_id) -> str:
    return f"/api/v1/meetings/{meeting_id}/recording/sessions"


def _start(client, headers, meeting_id, mime_type="audio/webm"):
    response = client.post(_base(meeting_id), headers=headers, json={"mime_type": mime_type})
    assert response.status_code == 201, response.text
    return response.json()["session_id"]


def _put(client, headers, meeting_id, session_id, index, data=None):
    response = client.put(
        f"{_base(meeting_id)}/{session_id}/chunks/{index}",
        headers={**headers, "Content-Type": "application/octet-stream"},
        content=data if data is not None else f"chunk-{index}".encode(),
    )
    assert response.status_code == 200, response.text


def _finish(client, headers, meeting_id, session_id, total_chunks):
    return client.post(
        f"{_base(meeting_id)}/{session_id}/finish", headers=headers, json={"total_chunks": total_chunks}
    )


def _session(db_session, session_id) -> RecordingSession:
    db_session.expire_all()
    return db_session.get(RecordingSession, uuid.UUID(session_id))


@pytest.fixture
def finalize_delays(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.tasks.recording_session.finalize_recording_session_task.delay", lambda *args: calls.append(args)
    )
    return calls


@pytest.fixture
def pipeline_delays(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.tasks.process_recording.process_recording_task.delay", lambda *args: calls.append(args)
    )
    return calls


@pytest.fixture
def recorded(client, make_user, make_meeting, auth_headers, fake_storage, finalize_delays):
    """Sesi dengan 3 potongan terkirim: (organizer, meeting, headers, session_id)."""
    organizer = make_user()
    meeting = make_meeting(organizer)
    headers = auth_headers(organizer)
    session_id = _start(client, headers, meeting.id)
    for index in range(3):
        _put(client, headers, meeting.id, session_id, index)
    return organizer, meeting, headers, session_id


# ------------------------------------------------------------ endpoint finish


def test_finish_with_complete_chunks_queues_finalize(client, db_session, recorded, finalize_delays):
    organizer, meeting, headers, session_id = recorded

    response = _finish(client, headers, meeting.id, session_id, 3)

    assert response.status_code == 202
    assert response.json() == {
        "session_id": session_id,
        "status": "finalizing",
        "chunk_count": 3,
        "error_message": None,
    }
    assert _session(db_session, session_id).status == "finalizing"
    assert finalize_delays == [(session_id,)]


def test_finish_with_missing_chunks_is_409_listing_the_missing_indices(
    client, db_session, make_user, make_meeting, auth_headers, fake_storage, finalize_delays
):
    organizer = make_user()
    meeting = make_meeting(organizer)
    headers = auth_headers(organizer)
    session_id = _start(client, headers, meeting.id)
    for index in (0, 2, 4):
        _put(client, headers, meeting.id, session_id, index)

    response = _finish(client, headers, meeting.id, session_id, 5)

    assert response.status_code == 409
    body = response.json()
    assert isinstance(body["detail"], str)
    assert body["missing_indices"] == [1, 3]
    assert _session(db_session, session_id).status == "recording"
    assert finalize_delays == []


def test_finish_ignores_chunks_beyond_total(client, db_session, recorded, finalize_delays):
    organizer, meeting, headers, session_id = recorded

    response = _finish(client, headers, meeting.id, session_id, 2)

    assert response.status_code == 202
    assert response.json()["chunk_count"] == 2


@pytest.mark.parametrize("total", [0, -1])
def test_finish_rejects_non_positive_total(client, recorded, finalize_delays, total):
    organizer, meeting, headers, session_id = recorded

    assert _finish(client, headers, meeting.id, session_id, total).status_code == 400
    assert finalize_delays == []


def test_finish_rejects_total_beyond_duration_limit(client, recorded, finalize_delays, monkeypatch):
    monkeypatch.setattr(settings, "MAX_AUDIO_DURATION_HOURS", 1)
    monkeypatch.setattr(settings, "RECORDING_CHUNK_SECONDS", 1800)
    monkeypatch.setattr(settings, "RECORDING_CHUNK_COUNT_TOLERANCE_PERCENT", 0)
    organizer, meeting, headers, session_id = recorded  # batas: 2 potongan

    assert _finish(client, headers, meeting.id, session_id, 3).status_code == 400


def test_finish_twice_does_not_queue_a_second_finalize(client, recorded, finalize_delays):
    organizer, meeting, headers, session_id = recorded

    first = _finish(client, headers, meeting.id, session_id, 3)
    second = _finish(client, headers, meeting.id, session_id, 3)

    assert first.status_code == 202 and second.status_code == 202
    assert second.json()["status"] == "finalizing"
    assert finalize_delays == [(session_id,)]


def test_finish_on_finalized_session_queues_nothing(client, db_session, recorded, finalize_delays):
    organizer, meeting, headers, session_id = recorded
    session = _session(db_session, session_id)
    session.status = "finalized"
    db_session.commit()

    response = _finish(client, headers, meeting.id, session_id, 3)

    assert response.status_code == 202
    assert response.json()["status"] == "finalized"
    assert finalize_delays == []


def test_finish_on_failed_session_retries(client, db_session, recorded, finalize_delays):
    organizer, meeting, headers, session_id = recorded
    session = _session(db_session, session_id)
    session.status = "failed"
    session.error_message = "Konversi audio gagal."
    db_session.commit()

    response = _finish(client, headers, meeting.id, session_id, 3)

    assert response.status_code == 202
    assert response.json()["status"] == "finalizing"
    assert response.json()["error_message"] is None
    assert finalize_delays == [(session_id,)]


def test_retry_of_failed_session_is_409_when_a_new_session_is_already_active(
    client, db_session, recorded, finalize_delays
):
    organizer, meeting, headers, session_id = recorded
    session = _session(db_session, session_id)
    session.status = "failed"
    db_session.commit()
    new_session_id = _start(client, headers, meeting.id)

    response = _finish(client, headers, meeting.id, session_id, 3)

    assert response.status_code == 409
    assert response.json()["session_id"] == new_session_id
    assert finalize_delays == []


def test_finish_on_abandoned_session_is_409(client, db_session, recorded, finalize_delays):
    organizer, meeting, headers, session_id = recorded
    session = _session(db_session, session_id)
    session.status = "abandoned"
    db_session.commit()

    assert _finish(client, headers, meeting.id, session_id, 3).status_code == 409
    assert finalize_delays == []


def test_finish_by_non_organizer_is_forbidden(
    client, make_user, make_meeting, auth_headers, fake_storage, finalize_delays
):
    organizer, member = make_user(), make_user()
    meeting = make_meeting(organizer, members=[member])
    session_id = _start(client, auth_headers(organizer), meeting.id)

    assert _finish(client, auth_headers(member), meeting.id, session_id, 1).status_code == 403


def test_finish_unknown_session_is_404(client, make_user, make_meeting, auth_headers):
    organizer = make_user()
    meeting = make_meeting(organizer)

    assert _finish(client, auth_headers(organizer), meeting.id, uuid.uuid4(), 1).status_code == 404


# ------------------------------------------------------------- task finalize


def _finish_and_finalize(client, headers, meeting, session_id, total=3):
    assert _finish(client, headers, meeting.id, session_id, total).status_code == 202
    finalize_recording_session_task(session_id)


def test_finalize_runs_the_same_pipeline_entry_as_upload(
    client, db_session, recorded, fake_storage, fake_converter, pipeline_delays
):
    organizer, meeting, headers, session_id = recorded

    _finish_and_finalize(client, headers, meeting, session_id)

    db_session.expire_all()
    recording = db_session.query(Recording).filter_by(meeting_id=meeting.id).one()
    assert recording.processing_status == ProcessingStatus.queued
    assert recording.size == len(TINY_M4A.read_bytes())
    assert recording.duration == pytest.approx(1.0, abs=0.2)
    assert recording.file_url.startswith(f"recordings/{meeting.id}/") and recording.file_url.endswith(".m4a")
    assert fake_storage.objects[recording.file_url] == TINY_M4A.read_bytes()
    assert db_session.get(Meeting, meeting.id).attendance_locked is True
    assert pipeline_delays == [(str(recording.id), str(meeting.id))]

    session = _session(db_session, session_id)
    assert session.status == "finalized"
    assert session.finished_at is not None
    assert session.error_message is None


def test_finalize_converts_the_chunks_once_as_one_byte_for_byte_stream(
    client, recorded, fake_converter, pipeline_delays
):
    organizer, meeting, headers, session_id = recorded

    _finish_and_finalize(client, headers, meeting, session_id)

    # Hanya potongan pertama berisi header, jadi harus digabung utuh lalu dikonversi SEKALI.
    assert fake_converter.inputs == [b"chunk-0chunk-1chunk-2"]
    assert fake_converter.settings == [(settings.RECORDING_OUTPUT_SAMPLE_RATE, settings.RECORDING_OUTPUT_BITRATE_KBPS)]


@pytest.mark.parametrize("mime_type,extension", [("audio/webm", ".webm"), ("audio/ogg", ".ogg"), ("audio/mp4", ".mp4")])
def test_finalize_gives_the_converter_an_input_named_after_the_recorded_format(
    client, make_user, make_meeting, auth_headers, fake_storage, fake_converter, pipeline_delays,
    finalize_delays, mime_type, extension,
):
    organizer = make_user()
    meeting = make_meeting(organizer)
    headers = auth_headers(organizer)
    session_id = _start(client, headers, meeting.id, mime_type)
    _put(client, headers, meeting.id, session_id, 0)

    _finish_and_finalize(client, headers, meeting, session_id, total=1)

    assert fake_converter.calls[0][0].endswith(extension)


def test_finalize_cleans_up_chunks_and_temp_files_on_success(
    client, recorded, fake_storage, fake_converter, pipeline_delays
):
    organizer, meeting, headers, session_id = recorded

    _finish_and_finalize(client, headers, meeting, session_id)

    assert [key for key in fake_storage.objects if key.startswith("recording-sessions/")] == []
    src, dst = fake_converter.calls[0]
    assert not Path(src).exists() and not Path(dst).exists()


def test_finalize_replaces_previous_results_like_a_replacement_upload(
    client, db_session, make_user, make_meeting, auth_headers, fake_storage, fake_converter,
    pipeline_delays, finalize_delays,
):
    organizer = make_user()
    meeting = make_meeting(organizer, with_notulen=True, with_recording=True, notulen_status=NotulenStatus.draft)
    old_recording_id = meeting.recording.id
    headers = auth_headers(organizer)
    session_id = _start(client, headers, meeting.id)
    _put(client, headers, meeting.id, session_id, 0)

    _finish_and_finalize(client, headers, meeting, session_id, total=1)

    db_session.expire_all()
    assert db_session.query(Transcript).filter_by(meeting_id=meeting.id).count() == 0
    assert db_session.query(Summary).filter_by(meeting_id=meeting.id).count() == 0
    assert db_session.query(ActionItem).filter_by(meeting_id=meeting.id).count() == 0
    assert db_session.get(Meeting, meeting.id).notulen_status is None
    recording = db_session.query(Recording).filter_by(meeting_id=meeting.id).one()
    assert recording.id != old_recording_id
    assert fake_storage.deleted_keys == ["meetings/x.mp3"]
    assert _session(db_session, session_id).status == "finalized"


def test_finalize_fails_with_clear_message_while_previous_recording_is_processed(
    client, db_session, recorded, fake_storage, fake_converter, pipeline_delays
):
    organizer, meeting, headers, session_id = recorded
    db_session.add(
        Recording(meeting_id=meeting.id, file_url="old.m4a", size=1, processing_status=ProcessingStatus.extracting)
    )
    db_session.commit()

    _finish_and_finalize(client, headers, meeting, session_id)

    session = _session(db_session, session_id)
    assert session.status == "failed"
    assert "Rekaman sebelumnya masih diproses AI" in session.error_message
    assert session.finished_at is not None
    assert len([key for key in fake_storage.objects if key.startswith("recording-sessions/")]) == 3  # dipertahankan
    assert fake_converter.calls == []
    assert pipeline_delays == []


def test_finalize_fails_when_conversion_fails_and_keeps_chunks_for_retry(
    client, db_session, recorded, fake_storage, fake_converter, pipeline_delays
):
    organizer, meeting, headers, session_id = recorded
    fake_converter.error = AudioConversionError("Konversi audio gagal: Invalid data found")

    _finish_and_finalize(client, headers, meeting, session_id)

    session = _session(db_session, session_id)
    assert session.status == "failed"
    assert session.error_message == "Konversi audio gagal: Invalid data found"
    assert db_session.query(Recording).filter_by(meeting_id=meeting.id).count() == 0
    assert len([key for key in fake_storage.objects if key.startswith("recording-sessions/")]) == 3
    src, dst = fake_converter.calls[0]
    assert not Path(src).exists() and not Path(dst).exists()
    assert pipeline_delays == []


def test_failed_session_can_be_retried_and_then_succeeds(
    client, db_session, recorded, fake_storage, fake_converter, pipeline_delays
):
    organizer, meeting, headers, session_id = recorded
    fake_converter.error = AudioConversionError("sementara gagal")
    _finish_and_finalize(client, headers, meeting, session_id)
    assert _session(db_session, session_id).status == "failed"

    fake_converter.error = None
    _finish_and_finalize(client, headers, meeting, session_id)

    assert _session(db_session, session_id).status == "finalized"
    assert _session(db_session, session_id).error_message is None
    assert len(pipeline_delays) == 1


def test_finalize_fails_when_converted_audio_exceeds_duration_limit(
    client, db_session, recorded, fake_storage, fake_converter, pipeline_delays, monkeypatch
):
    organizer, meeting, headers, session_id = recorded
    assert _finish(client, headers, meeting.id, session_id, 3).status_code == 202
    monkeypatch.setattr(settings, "MAX_AUDIO_DURATION_HOURS", 0)

    finalize_recording_session_task(session_id)

    session = _session(db_session, session_id)
    assert session.status == "failed"
    assert session.error_message.startswith("Durasi audio")
    assert db_session.query(Recording).filter_by(meeting_id=meeting.id).count() == 0
    assert len([key for key in fake_storage.objects if key.startswith("recording-sessions/")]) == 3


def test_finalize_fails_when_converted_audio_exceeds_size_limit(
    client, db_session, recorded, fake_storage, fake_converter, pipeline_delays, monkeypatch
):
    organizer, meeting, headers, session_id = recorded
    assert _finish(client, headers, meeting.id, session_id, 3).status_code == 202
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0)

    finalize_recording_session_task(session_id)

    session = _session(db_session, session_id)
    assert session.status == "failed"
    assert session.error_message == "File exceeds maximum size of 0MB"


def test_finalize_fails_clearly_when_a_chunk_has_disappeared_from_storage(
    client, db_session, recorded, fake_storage, fake_converter, pipeline_delays
):
    organizer, meeting, headers, session_id = recorded
    assert _finish(client, headers, meeting.id, session_id, 3).status_code == 202
    middle = [key for key in fake_storage.objects if key.endswith("000001")][0]
    del fake_storage.objects[middle]

    finalize_recording_session_task(session_id)

    session = _session(db_session, session_id)
    assert session.status == "failed"
    assert "Potongan" in session.error_message
    assert fake_converter.calls == []


@pytest.mark.parametrize("status", ["recording", "finalized", "failed", "abandoned"])
def test_finalize_does_nothing_unless_session_is_finalizing(
    client, db_session, recorded, fake_converter, pipeline_delays, status
):
    organizer, meeting, headers, session_id = recorded
    session = _session(db_session, session_id)
    session.status = status
    db_session.commit()

    finalize_recording_session_task(session_id)

    assert fake_converter.calls == []
    assert _session(db_session, session_id).status == status
    assert pipeline_delays == []


def test_finalize_for_unknown_session_does_not_crash(fake_converter):
    finalize_recording_session_task(str(uuid.uuid4()))

    assert fake_converter.calls == []
