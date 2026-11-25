"""Tes karakterisasi untuk POST /meetings/{id}/recording (upload manual).

Ditulis SEBELUM upload dipindah ke jalur penyimpanan hasil yang dipakai bersama rekam
langsung, dan harus hijau sebelum maupun sesudah pemindahan: perilaku upload (status,
pesan, urutan pemeriksaan, efek samping) tidak boleh berubah sedikit pun."""
import io
import uuid
import wave
from datetime import datetime, timezone
from pathlib import Path

import pytest

from app.config import settings
from app.models.action_item import ActionItem, ActionItemSource
from app.models.meeting import Meeting, NotulenStatus
from app.models.recording import ProcessingStatus, Recording
from app.models.summary import Summary
from app.models.transcript import Transcript

TINY_M4A = Path(__file__).resolve().parent / "fixtures" / "tiny.m4a"


def _wav(seconds: int = 1) -> bytes:
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(1)
        writer.setframerate(8000)
        writer.writeframes(b"\x80" * 8000 * seconds)
    return buffer.getvalue()


def _upload(client, headers, meeting_id, filename: str = "rapat.wav", data: bytes | None = None):
    return client.post(
        f"/api/v1/meetings/{meeting_id}/recording",
        headers=headers,
        files={"file": (filename, _wav() if data is None else data, "application/octet-stream")},
    )


@pytest.fixture
def delays(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.tasks.process_recording.process_recording_task.delay", lambda *args: calls.append(args)
    )
    return calls


@pytest.fixture
def organizer_meeting(make_user, make_meeting):
    organizer = make_user()
    return organizer, make_meeting(organizer)


def _recording_of(db_session, meeting_id):
    db_session.expire_all()
    return db_session.query(Recording).filter_by(meeting_id=meeting_id).first()


# ------------------------------------------------------------------- sukses


def test_upload_creates_queued_recording_locks_attendance_and_enqueues_pipeline(
    client, db_session, organizer_meeting, auth_headers, fake_storage, delays
):
    organizer, meeting = organizer_meeting
    data = _wav(1)
    assert meeting.attendance_locked is False

    response = _upload(client, auth_headers(organizer), meeting.id, "rapat.wav", data)

    assert response.status_code == 202
    body = response.json()
    assert set(body) == {"id", "file_url", "duration", "size", "uploaded_at", "processing_status"}
    assert body["processing_status"] == "queued"
    assert body["size"] == len(data)
    assert body["duration"] == pytest.approx(1.0, abs=0.01)
    assert body["file_url"].startswith(f"recordings/{meeting.id}/") and body["file_url"].endswith(".wav")
    assert fake_storage.objects[body["file_url"]] == data

    recording = _recording_of(db_session, meeting.id)
    assert str(recording.id) == body["id"]
    assert recording.processing_status == ProcessingStatus.queued
    db_session.refresh(meeting)
    assert meeting.attendance_locked is True
    assert meeting.status.value == "scheduled"  # baru diubah oleh task Celery, bukan saat upload
    assert delays == [(body["id"], str(meeting.id))]


@pytest.mark.parametrize("filename", ["rapat.m4a", "rapat.mp4"])
def test_upload_accepts_mp4_family_audio(client, organizer_meeting, auth_headers, fake_storage, delays, filename):
    organizer, meeting = organizer_meeting

    response = _upload(client, auth_headers(organizer), meeting.id, filename, TINY_M4A.read_bytes())

    assert response.status_code == 202


def test_upload_extension_is_case_insensitive(client, organizer_meeting, auth_headers, fake_storage, delays):
    organizer, meeting = organizer_meeting

    response = _upload(client, auth_headers(organizer), meeting.id, "RAPAT.WAV")

    assert response.status_code == 202
    assert response.json()["file_url"].endswith(".wav")


# ----------------------------------------------------------- hak akses / 404


def test_upload_for_unknown_meeting_is_404(client, make_user, auth_headers, fake_storage, delays):
    response = _upload(client, auth_headers(make_user()), uuid.uuid4())

    assert response.status_code == 404
    assert response.json() == {"detail": "Meeting not found"}


def test_upload_does_not_filter_soft_deleted_meetings(
    client, db_session, organizer_meeting, auth_headers, fake_storage, delays
):
    # Perilaku saat ini (berbeda dari endpoint sesi rekam langsung): upload tidak
    # memeriksa Meeting.deleted_at. Dikunci apa adanya agar refactor tidak mengubahnya.
    organizer, meeting = organizer_meeting
    meeting.deleted_at = datetime.now(timezone.utc)
    db_session.commit()

    assert _upload(client, auth_headers(organizer), meeting.id).status_code == 202


def test_upload_by_participant_who_is_not_organizer_is_403(client, make_user, make_meeting, auth_headers, fake_storage, delays):
    organizer, member = make_user(), make_user()
    meeting = make_meeting(organizer, members=[member])

    response = _upload(client, auth_headers(member), meeting.id)

    assert response.status_code == 403
    assert response.json() == {"detail": "Only organizer can perform this action"}
    assert fake_storage.objects == {}


def test_upload_by_stranger_is_403(client, make_user, make_meeting, auth_headers, fake_storage, delays):
    meeting = make_meeting(make_user())

    assert _upload(client, auth_headers(make_user()), meeting.id).status_code == 403


# --------------------------------------------------------------- validasi


def test_upload_rejected_while_previous_recording_is_processed(
    client, db_session, organizer_meeting, auth_headers, fake_storage, delays
):
    organizer, meeting = organizer_meeting
    db_session.add(Recording(meeting_id=meeting.id, file_url="old.wav", size=1, processing_status=ProcessingStatus.extracting))
    db_session.commit()

    response = _upload(client, auth_headers(organizer), meeting.id)

    assert response.status_code == 409
    assert response.json()["detail"] == (
        "Rekaman sebelumnya masih diproses AI (status: extracting). Tunggu sampai selesai "
        "atau gagal sebelum mengganti/menghapus rekaman ini."
    )
    assert fake_storage.objects == {} and delays == []


def test_pipeline_conflict_is_checked_before_file_format(
    client, db_session, organizer_meeting, auth_headers, fake_storage, delays
):
    organizer, meeting = organizer_meeting
    db_session.add(Recording(meeting_id=meeting.id, file_url="old.wav", size=1, processing_status=ProcessingStatus.queued))
    db_session.commit()

    response = _upload(client, auth_headers(organizer), meeting.id, "dokumen.txt")

    assert response.status_code == 409


@pytest.mark.parametrize("filename", ["dokumen.txt", "tanpa-ekstensi", ".wav.exe"])
def test_upload_rejects_disallowed_extension(client, organizer_meeting, auth_headers, fake_storage, delays, filename):
    organizer, meeting = organizer_meeting

    response = _upload(client, auth_headers(organizer), meeting.id, filename)

    assert response.status_code == 400
    assert response.json()["detail"] == f"Invalid file format. Allowed: {', '.join(settings.allowed_audio_formats_list)}"
    assert fake_storage.objects == {} and delays == []


def test_upload_over_size_limit_is_413(client, organizer_meeting, auth_headers, fake_storage, delays, monkeypatch):
    monkeypatch.setattr(settings, "MAX_UPLOAD_SIZE_MB", 0)
    organizer, meeting = organizer_meeting

    response = _upload(client, auth_headers(organizer), meeting.id)

    assert response.status_code == 413
    assert response.json() == {"detail": "File exceeds maximum size of 0MB"}
    assert fake_storage.objects == {} and delays == []


def test_openai_size_limit_does_not_apply_to_gemini_provider(
    client, organizer_meeting, auth_headers, fake_storage, delays, monkeypatch
):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "gemini")
    monkeypatch.setattr(settings, "OPENAI_TRANSCRIBE_MAX_UPLOAD_MB", 0)
    organizer, meeting = organizer_meeting

    assert _upload(client, auth_headers(organizer), meeting.id).status_code == 202


def test_upload_openai_limit_message(client, make_user, make_meeting, auth_headers, fake_storage, delays, monkeypatch):
    monkeypatch.setattr(settings, "LLM_PROVIDER", "openai")
    monkeypatch.setattr(settings, "OPENAI_TRANSCRIBE_MAX_UPLOAD_MB", 0)
    organizer = make_user()
    meeting = make_meeting(organizer)

    response = _upload(client, auth_headers(organizer), meeting.id)

    assert response.status_code == 413
    assert response.json()["detail"] == (
        "File terlalu besar untuk provider OpenAI (maks. 0MB). Gunakan file yang lebih kecil, "
        "atau hubungi admin untuk beralih ke provider Gemini."
    )
    assert fake_storage.objects == {} and delays == []


def test_upload_that_is_not_audio_is_400(client, organizer_meeting, auth_headers, fake_storage, delays):
    organizer, meeting = organizer_meeting

    response = _upload(client, auth_headers(organizer), meeting.id, "rapat.wav", b"ini bukan audio sama sekali")

    assert response.status_code == 400
    assert response.json() == {"detail": "File tidak dapat dibaca sebagai audio yang valid."}
    assert fake_storage.objects == {} and delays == []


def test_upload_whose_content_does_not_match_extension_is_400(
    client, organizer_meeting, auth_headers, fake_storage, delays
):
    organizer, meeting = organizer_meeting

    # Isinya WAV valid tapi diklaim mp3.
    response = _upload(client, auth_headers(organizer), meeting.id, "rapat.mp3")

    assert response.status_code == 400
    assert response.json() == {"detail": "Isi file tidak sesuai dengan ekstensi yang diklaim."}
    assert fake_storage.objects == {} and delays == []


def test_upload_over_duration_limit_is_400(client, organizer_meeting, auth_headers, fake_storage, delays, monkeypatch):
    monkeypatch.setattr(settings, "MAX_AUDIO_DURATION_HOURS", 0)
    organizer, meeting = organizer_meeting

    response = _upload(client, auth_headers(organizer), meeting.id)

    assert response.status_code == 400
    assert response.json() == {"detail": "Durasi audio (0.0 jam) melebihi batas maksimum 0 jam."}
    assert fake_storage.objects == {} and delays == []


# --------------------------------------------------------------- penggantian


def test_replacement_clears_old_results_but_keeps_manual_action_items(
    client, db_session, make_user, make_meeting, auth_headers, fake_storage, delays
):
    organizer, member = make_user(), make_user()
    meeting = make_meeting(
        organizer,
        members=[member],
        with_notulen=True,
        with_recording=True,
        notulen_status=NotulenStatus.draft,
    )
    meeting.notulen_edited_at = datetime.now(timezone.utc)
    db_session.add(ActionItem(meeting_id=meeting.id, task="Tugas manual", source=ActionItemSource.manual))
    db_session.commit()
    old_recording_id = meeting.recording.id

    response = _upload(client, auth_headers(organizer), meeting.id)

    assert response.status_code == 202
    db_session.expire_all()
    meeting = db_session.get(Meeting, meeting.id)
    assert db_session.query(Transcript).filter_by(meeting_id=meeting.id).count() == 0
    assert db_session.query(Summary).filter_by(meeting_id=meeting.id).count() == 0
    remaining = db_session.query(ActionItem).filter_by(meeting_id=meeting.id).all()
    assert [(item.task, item.source) for item in remaining] == [("Tugas manual", ActionItemSource.manual)]
    assert meeting.notulen_status is None
    assert meeting.notulen_edited_at is None
    recording = _recording_of(db_session, meeting.id)
    assert recording.id != old_recording_id
    assert recording.processing_status == ProcessingStatus.queued
    assert delays == [(str(recording.id), str(meeting.id))]


def test_replacement_deletes_old_audio_file_after_commit(
    client, db_session, make_user, make_meeting, auth_headers, fake_storage, delays
):
    organizer = make_user()
    meeting = make_meeting(organizer, with_recording=True)  # file lama: meetings/x.mp3

    response = _upload(client, auth_headers(organizer), meeting.id)

    assert response.status_code == 202
    assert fake_storage.deleted_keys == ["meetings/x.mp3"]
    assert response.json()["file_url"] in fake_storage.objects


def test_first_upload_deletes_nothing(client, organizer_meeting, auth_headers, fake_storage, delays):
    organizer, meeting = organizer_meeting

    _upload(client, auth_headers(organizer), meeting.id)

    assert fake_storage.deleted_keys == []


# --------------------------------------------------------- balapan / re-cek


def test_recheck_after_storage_upload_rejects_and_removes_new_object(
    client, db_session, make_user, make_meeting, auth_headers, fake_storage, delays, monkeypatch
):
    # Upload ke storage bisa lama; kalau selama itu rekaman lama mulai diproses AI,
    # upload ditolak 409 dan objek yang sudah terlanjur disimpan dihapus lagi.
    organizer = make_user()
    meeting = make_meeting(organizer, with_recording=True)  # completed -> boleh diganti
    real_upload = fake_storage.upload_file

    def upload_then_celery_starts(file_bytes, filename, meeting_id):
        key = real_upload(file_bytes, filename, meeting_id)
        old = db_session.query(Recording).filter_by(meeting_id=meeting.id).first()
        old.processing_status = ProcessingStatus.transcribing
        db_session.commit()
        return key

    monkeypatch.setattr("app.services.storage.upload_file", upload_then_celery_starts)

    response = _upload(client, auth_headers(organizer), meeting.id)

    assert response.status_code == 409
    assert response.json()["detail"].startswith("Rekaman sebelumnya masih diproses AI (status: transcribing)")
    assert len(fake_storage.deleted_keys) == 1
    assert fake_storage.deleted_keys[0] not in fake_storage.objects
    assert "meetings/x.mp3" not in fake_storage.deleted_keys  # file lama tidak disentuh
    assert delays == []


def test_simultaneous_upload_losing_the_unique_constraint_is_409_and_cleans_up(
    client, db_session, organizer_meeting, auth_headers, fake_storage, delays, monkeypatch
):
    # Upload lain menyelip tepat sebelum commit dan lolos semua pemeriksaan; constraint
    # unik Recording.meeting_id yang menolak. Yang kalah tidak boleh meninggalkan objek yatim.
    organizer, meeting = organizer_meeting
    real_upload = fake_storage.upload_file

    def upload_then_rival_commits(file_bytes, filename, meeting_id):
        key = real_upload(file_bytes, filename, meeting_id)
        db_session.add(Recording(meeting_id=meeting.id, file_url="rival.wav", size=1, processing_status=ProcessingStatus.completed))
        db_session.commit()
        return key

    monkeypatch.setattr("app.services.storage.upload_file", upload_then_rival_commits)
    # Rival "tidak terlihat" oleh langkah pembersihan; hanya constraint yang menahannya.
    monkeypatch.setattr("app.services.recording._clear_previous_processing", lambda db, recording, meeting: None)

    response = _upload(client, auth_headers(organizer), meeting.id)

    assert response.status_code == 409
    assert response.json() == {"detail": "Rekaman lain untuk meeting ini baru saja diupload secara bersamaan. Coba lagi."}
    assert len(fake_storage.deleted_keys) == 1
    assert fake_storage.deleted_keys[0] not in fake_storage.objects
    assert delays == []
