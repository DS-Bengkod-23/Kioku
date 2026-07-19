import io
import uuid
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile
from mutagen import File as MutagenFile
from mutagen.mp3 import MP3
from mutagen.mp4 import MP4
from mutagen.wave import WAVE

from app.config import settings
from app.models.meeting import Meeting
from app.models.participant import MeetingParticipant, ParticipantRole
from app.models.recording import Recording, ProcessingStatus
from app.models.transcript import Transcript
from app.models.summary import Summary
from app.models.action_item import ActionItem, ActionItemSource
from app.services import storage

_AUDIO_CONTENT_TYPE_BY_EXT = {
    "mp3": "audio/mpeg",
    "mp4": "audio/mp4",
    "wav": "audio/wav",
    "m4a": "audio/x-m4a",
}

# OpenAI /v1/audio/transcriptions hard-cap 25MB, berlaku endpoint-wide untuk
# whisper-1/gpt-4o-transcribe/gpt-4o-mini-transcribe — bukan per-model, tidak
# bisa diubah lewat konfigurasi. Dicek di sini supaya gagalnya kelihatan saat
# upload (backend-api), bukan menit kemudian di dalam Celery.
_OPENAI_TRANSCRIBE_MAX_BYTES = 25 * 1024 * 1024
_MUTAGEN_TYPE_BY_EXT = {"mp3": MP3, "mp4": MP4, "m4a": MP4, "wav": WAVE}

# Status di mana Celery task masih aktif memproses recording ini. Upload ulang
# atau hapus saat status di sini akan membuat task lama menulis ke row yang
# sudah diganti/dihapus (race condition), jadi keduanya diblokir di endpoint.
_PIPELINE_ACTIVE_STATUSES = {
    ProcessingStatus.queued,
    ProcessingStatus.transcribing,
    ProcessingStatus.diarizing,
    ProcessingStatus.extracting,
    ProcessingStatus.sending_email,
}


def _reject_if_pipeline_active(recording: Recording | None) -> None:
    if recording is not None and recording.processing_status in _PIPELINE_ACTIVE_STATUSES:
        raise HTTPException(
            status_code=409,
            detail="Rekaman sebelumnya masih diproses AI (status: "
                   f"{recording.processing_status.value}). Tunggu sampai selesai atau "
                   "gagal sebelum mengganti/menghapus rekaman ini.",
        )


def _get_meeting_or_404(db: Session, meeting_id: uuid.UUID) -> Meeting:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
    return meeting


def _require_organizer(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID):
    participant = (
        db.query(MeetingParticipant)
        .filter(
            MeetingParticipant.meeting_id == meeting_id,
            MeetingParticipant.user_id == user_id,
            MeetingParticipant.role == ParticipantRole.organizer,
        )
        .first()
    )
    if not participant:
        raise HTTPException(status_code=403, detail="Only organizer can perform this action")


def _require_participant(meeting: Meeting, user_id: uuid.UUID):
    if not any(p.user_id == user_id for p in meeting.participants):
        raise HTTPException(status_code=403, detail="Not authorized to access this meeting")


def _delete_recording_records(db: Session, recording: Recording, meeting_id: uuid.UUID) -> None:
    # Hanya action item ber-source AI yang dihapus di sini — action item yang
    # ditambahkan manual oleh organizer harus tetap ada walau rekamannya diganti/dihapus
    # (konsisten dengan reprocessing di tasks/process_recording.py).
    db.query(ActionItem).filter(
        ActionItem.meeting_id == meeting_id,
        ActionItem.source == ActionItemSource.ai,
    ).delete()
    db.query(Summary).filter(Summary.meeting_id == meeting_id).delete()
    db.query(Transcript).filter(Transcript.meeting_id == meeting_id).delete()
    db.delete(recording)


async def upload_recording(
    db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, file: UploadFile
) -> Recording:
    meeting = _get_meeting_or_404(db, meeting_id)
    _require_organizer(db, meeting_id, user_id)

    existing = db.query(Recording).filter(Recording.meeting_id == meeting_id).first()
    _reject_if_pipeline_active(existing)

    allowed = settings.allowed_audio_formats_list
    ext = (file.filename or "").rsplit(".", 1)[-1].lower() if file.filename and "." in file.filename else ""
    if ext not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid file format. Allowed: {', '.join(allowed)}",
        )

    file_bytes = await file.read()
    size = len(file_bytes)
    max_bytes = settings.MAX_UPLOAD_SIZE_MB * 1024 * 1024
    if size > max_bytes:
        raise HTTPException(
            status_code=413,
            detail=f"File exceeds maximum size of {settings.MAX_UPLOAD_SIZE_MB}MB",
        )

    if settings.LLM_PROVIDER == "openai" and size > _OPENAI_TRANSCRIBE_MAX_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"File terlalu besar untuk provider OpenAI (maks. "
                    f"{_OPENAI_TRANSCRIBE_MAX_BYTES // (1024 * 1024)}MB). Gunakan file "
                    f"yang lebih kecil, atau hubungi admin untuk beralih ke provider Gemini.",
        )

    try:
        audio = MutagenFile(io.BytesIO(file_bytes))
    except Exception:
        audio = None
    if audio is None or audio.info is None:
        raise HTTPException(status_code=400, detail="File tidak dapat dibaca sebagai audio yang valid.")

    expected_type = _MUTAGEN_TYPE_BY_EXT.get(ext)
    if expected_type and not isinstance(audio, expected_type):
        raise HTTPException(status_code=400, detail="Isi file tidak sesuai dengan ekstensi yang diklaim.")

    duration_seconds = audio.info.length
    if duration_seconds > settings.max_audio_duration_seconds:
        raise HTTPException(
            status_code=400,
            detail=f"Durasi audio ({duration_seconds / 3600:.1f} jam) melebihi batas "
                    f"maksimum {settings.MAX_AUDIO_DURATION_HOURS} jam.",
        )

    object_key = storage.upload_file(file_bytes, file.filename or f"audio.{ext}", str(meeting_id))

    # Re-cek: upload ke storage di atas bisa makan waktu untuk file besar, jadi
    # status recording lama bisa saja berubah (mis. Celery baru mulai memproses)
    # sejak pengecekan di awal fungsi.
    db.expire(existing) if existing else None
    existing = db.query(Recording).filter(Recording.meeting_id == meeting_id).first()
    try:
        _reject_if_pipeline_active(existing)
    except HTTPException:
        storage.delete_file(object_key)
        raise

    old_file_url = existing.file_url if existing else None
    if existing:
        _delete_recording_records(db, existing, meeting_id)

    recording = Recording(
        meeting_id=meeting_id,
        file_url=object_key,
        size=size,
        duration=duration_seconds,
        processing_status=ProcessingStatus.queued,
    )
    db.add(recording)

    # Lock attendance segera saat recording diupload — sinyal meeting sudah selesai
    meeting.attendance_locked = True

    try:
        db.commit()
    except IntegrityError:
        # Dua upload konkuren ke meeting yang sama bisa lolos pengecekan _reject_if_
        # pipeline_active/`existing` sebelum salah satunya commit lebih dulu (unique
        # constraint di Recording.meeting_id). Yang kalah tidak boleh menyisakan file
        # yang sudah kadung diupload ke storage sebagai objek yatim.
        db.rollback()
        storage.delete_file(object_key)
        raise HTTPException(
            status_code=409,
            detail="Rekaman lain untuk meeting ini baru saja diupload secara bersamaan. Coba lagi.",
        )
    db.refresh(recording)

    if old_file_url:
        storage.delete_file(old_file_url)  # best-effort, sudah menelan ClientError di dalamnya

    from app.tasks.process_recording import process_recording_task  # noqa: PLC0415
    process_recording_task.delay(str(recording.id), str(meeting_id))

    return recording


def get_recording_status(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Recording:
    meeting = _get_meeting_or_404(db, meeting_id)
    _require_participant(meeting, user_id)

    recording = db.query(Recording).filter(Recording.meeting_id == meeting_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    return recording


def _iter_and_close(body):
    try:
        for chunk in body.iter_chunks(chunk_size=64 * 1024):
            yield chunk
    finally:
        body.close()


def get_recording_audio(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID):
    """Auth sama seperti get_recording_status: organizer ATAU participant boleh
    akses. Return (byte_iterator, content_type, content_length) untuk di-stream
    balik lewat StreamingResponse di router -- proxy authenticated, bukan
    presigned URL, supaya MinIO tidak perlu diekspos ke browser."""
    meeting = _get_meeting_or_404(db, meeting_id)
    _require_participant(meeting, user_id)

    recording = db.query(Recording).filter(Recording.meeting_id == meeting_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    ext = recording.file_url.rsplit(".", 1)[-1].lower() if "." in recording.file_url else ""
    content_type = _AUDIO_CONTENT_TYPE_BY_EXT.get(ext, "application/octet-stream")

    try:
        body = storage.get_file_stream(recording.file_url)
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="Recording file not found in storage")

    return _iter_and_close(body), content_type, recording.size


def delete_recording(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID):
    _get_meeting_or_404(db, meeting_id)
    _require_organizer(db, meeting_id, user_id)

    recording = db.query(Recording).filter(Recording.meeting_id == meeting_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")
    _reject_if_pipeline_active(recording)

    storage.delete_file(recording.file_url)

    _delete_recording_records(db, recording, meeting_id)
    db.commit()
