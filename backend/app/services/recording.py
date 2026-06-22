import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, UploadFile

from app.config import settings
from app.models.meeting import Meeting
from app.models.participant import MeetingParticipant, ParticipantRole
from app.models.recording import Recording, ProcessingStatus
from app.models.transcript import Transcript
from app.models.summary import Summary
from app.models.action_item import ActionItem
from app.services import storage


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

    object_key = storage.upload_file(file_bytes, file.filename or f"audio.{ext}", str(meeting_id))

    recording = Recording(
        meeting_id=meeting_id,
        file_url=object_key,
        size=size,
        processing_status=ProcessingStatus.queued,
    )
    db.add(recording)

    # Lock attendance segera saat recording diupload — sinyal meeting sudah selesai
    meeting.attendance_locked_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(recording)

    from app.tasks.process_recording import process_recording_task  # noqa: PLC0415
    process_recording_task.delay(str(recording.id), str(meeting_id))

    return recording


def get_recording_status(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Recording:
    _get_meeting_or_404(db, meeting_id)

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

    db.query(ActionItem).filter(ActionItem.meeting_id == meeting_id).delete()
    db.query(Summary).filter(Summary.meeting_id == meeting_id).delete()
    db.query(Transcript).filter(Transcript.meeting_id == meeting_id).delete()
    db.delete(recording)
    db.commit()
