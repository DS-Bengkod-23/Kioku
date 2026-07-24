from pydantic import BaseModel, ConfigDict, Field, model_validator
from typing import List, Literal, Optional, Any
from datetime import datetime
from uuid import UUID
from app.schemas.recording import RecordingResponse


class MeetingCreate(BaseModel):
    title: str
    scheduled_at: datetime
    location: Optional[str] = None
    location_building: Optional[str] = None
    location_room: Optional[str] = None
    location_city: Optional[str] = None
    description: Optional[str] = None
    agenda_text: Optional[str] = None
    participant_emails: List[str]
    duration_minutes: int = Field(60, ge=1, description="Durasi rapat dalam menit, minimal 1")


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    location: Optional[str] = None
    location_building: Optional[str] = None
    location_room: Optional[str] = None
    location_city: Optional[str] = None
    description: Optional[str] = None
    agenda_text: Optional[str] = None
    duration_minutes: Optional[int] = Field(None, ge=1, description="Durasi rapat dalam menit, minimal 1")
    participant_emails: Optional[List[str]] = None


class ParticipantResponse(BaseModel):
    id: UUID
    email: str
    name: Optional[str] = None
    role: str
    attendance_status: str
    rsvp_status: str
    rsvp_reason: Optional[str] = None
    checkin_token: Optional[str] = None

    @model_validator(mode='before')
    @classmethod
    def extract_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data

        name = data.user.name if getattr(data, 'user', None) else None

        attendance_status = "pending"
        if getattr(data, 'attendance', None):
            attendance_status = data.attendance.status.value if hasattr(data.attendance.status, 'value') else data.attendance.status

        role = data.role.value if hasattr(data.role, 'value') else data.role

        rsvp_status = data.rsvp_status.value if hasattr(data.rsvp_status, 'value') else data.rsvp_status

        checkin_token = data.invitation.token if getattr(data, 'invitation', None) else None

        return {
            "id": data.id,
            "email": data.email,
            "name": name,
            "role": role,
            "attendance_status": attendance_status,
            "rsvp_status": rsvp_status,
            "rsvp_reason": data.rsvp_reason,
            "checkin_token": checkin_token,
        }


class RsvpRequest(BaseModel):
    response: Literal["akan_hadir", "tidak_hadir"]
    reason: Optional[str] = None


class MeetingListItem(BaseModel):
    id: UUID
    title: str
    scheduled_at: datetime
    location: Optional[str] = None
    status: str
    participant_count: int
    attendance_count: int
    has_recording: bool
    processing_status: Optional[str] = None
    deleted_at: Optional[datetime] = None

    @model_validator(mode='before')
    @classmethod
    def extract_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data

        status = data.status.value if hasattr(data.status, 'value') else data.status

        participant_count = len(data.participants) if hasattr(data, 'participants') else 0
        attendance_count = sum(1 for p in (data.participants if hasattr(data, 'participants') else []) if p.attendance and p.attendance.status.value == "hadir")

        recording = data.recording if getattr(data, 'recording', None) and data.recording.deleted_at is None else None
        has_recording = recording is not None
        processing_status = getattr(recording, 'processing_status', None) if has_recording else None
        if processing_status and hasattr(processing_status, 'value'):
            processing_status = processing_status.value

        return {
            "id": data.id,
            "title": data.title,
            "scheduled_at": data.scheduled_at,
            "location": data.location,
            "status": status,
            "participant_count": participant_count,
            "attendance_count": attendance_count,
            "has_recording": has_recording,
            "processing_status": processing_status,
            "deleted_at": getattr(data, 'deleted_at', None),
        }


class MeetingListResponse(BaseModel):
    items: List[MeetingListItem]
    total: int
    page: int
    limit: int


class MeetingDeletedNotice(BaseModel):
    id: UUID
    deleted: bool = True
    message: str = "Meeting ini telah dihapus oleh admin."


class OrganizerResponse(BaseModel):
    id: UUID
    name: str
    email: str

    model_config = ConfigDict(from_attributes=True)


class MeetingDetail(BaseModel):
    id: UUID
    title: str
    scheduled_at: datetime
    location: Optional[str] = None
    location_building: Optional[str] = None
    location_room: Optional[str] = None
    location_city: Optional[str] = None
    description: Optional[str] = None
    agenda_text: Optional[str] = None
    status: str
    duration_minutes: int
    attendance_locked: bool = False
    organizer: OrganizerResponse
    participants: List[ParticipantResponse]
    recording: Optional[RecordingResponse] = None
    processing_status: Optional[str] = None
    transcript: Optional[Any] = None
    summary: Optional[Any] = None
    action_items: Optional[List[Any]] = None

    @model_validator(mode='before')
    @classmethod
    def extract_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
        if not hasattr(data, 'organizer'):
            # Not a Meeting ORM instance (e.g. a MeetingDeletedNotice already
            # constructed by the router) — let the Union try the next member
            # instead of crashing on a raw AttributeError.
            raise ValueError("Expected a Meeting ORM instance")

        status = data.status.value if hasattr(data.status, 'value') else data.status

        recording = data.recording if getattr(data, 'recording', None) and data.recording.deleted_at is None else None
        has_recording = recording is not None
        processing_status = getattr(recording, 'processing_status', None) if has_recording else None
        if processing_status and hasattr(processing_status, 'value'):
            processing_status = processing_status.value

        transcript = None
        if getattr(data, "transcript", None):
            t = data.transcript
            transcript = {"id": str(t.id), "segments": t.segments}

        summary = None
        if getattr(data, "summary", None):
            s = data.summary
            summary = {"id": str(s.id), "tldr": s.tldr, "decisions": s.decisions, "topics": s.topics}

        action_items = [
            {
                "id": str(ai.id),
                "task": ai.task,
                "assignee_participant_id": str(ai.assignee_participant_id) if ai.assignee_participant_id else None,
                "assignee": (
                    {
                        "id": str(ai.assignee_participant.user.id),
                        "name": ai.assignee_participant.user.name,
                        "email": ai.assignee_participant.user.email,
                    }
                    if ai.assignee_participant and ai.assignee_participant.user
                    else None
                ),
                "due_date": ai.due_date.isoformat() if ai.due_date else None,
                "status": ai.status.value if hasattr(ai.status, "value") else ai.status,
            }
            for ai in (getattr(data, "action_items", None) or [])
        ]

        return {
            "id": data.id,
            "title": data.title,
            "scheduled_at": data.scheduled_at,
            "location": data.location,
            "location_building": data.location_building,
            "location_room": data.location_room,
            "location_city": data.location_city,
            "description": data.description,
            "agenda_text": data.agenda_text,
            "status": status,
            "duration_minutes": data.duration_minutes,
            "attendance_locked": data.attendance_locked,
            "organizer": data.organizer,
            "participants": data.participants,
            "recording": recording,
            "processing_status": processing_status,
            "transcript": transcript,
            "summary": summary,
            "action_items": action_items,
        }
