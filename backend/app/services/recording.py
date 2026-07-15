import io
import uuid
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
from app.models.action_item import ActionItem
from app.services import storage

# OpenAI /v1/audio/transcriptions hard-cap 25MB, berlaku endpoint-wide untuk
# whisper-1/gpt-4o-transcribe/gpt-4o-mini-transcribe — bukan per-model, tidak
# bisa diubah lewat konfigurasi. Dicek di sini supaya gagalnya kelihatan saat
# upload (backend-api), bukan menit kemudian di dalam Celery.
_OPENAI_TRANSCRIBE_MAX_BYTES = 25 * 1024 * 1024
_MUTAGEN_TYPE_BY_EXT = {"mp3": MP3, "mp4": MP4, "m4a": MP4, "wav": WAVE}


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
    db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).delete()
    db.query(Summary).filter(Summary.meeting_id == meeting_id).delete()
    db.query(Transcript).filter(Transcript.meeting_id == meeting_id).delete()
    db.delete(recording)


async def upload_recording(
    db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, file: UploadFile
) -> Recording:
    meeting = _get_meeting_or_404(db, meeting_id)
    _require_organizer(db, meeting_id, user_id)

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

    existing = db.query(Recording).filter(Recording.meeting_id == meeting_id).first()
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

    db.commit()
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


def delete_recording(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID):
    _get_meeting_or_404(db, meeting_id)
    _require_organizer(db, meeting_id, user_id)

    recording = db.query(Recording).filter(Recording.meeting_id == meeting_id).first()
    if not recording:
        raise HTTPException(status_code=404, detail="Recording not found")

    storage.delete_file(recording.file_url)

    _delete_recording_records(db, recording, meeting_id)
    db.commit()
