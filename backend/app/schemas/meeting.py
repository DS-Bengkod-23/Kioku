from pydantic import BaseModel, ConfigDict, model_validator
from typing import List, Optional, Any
from datetime import datetime
from uuid import UUID
from app.schemas.recording import RecordingResponse


class MeetingCreate(BaseModel):
    title: str
    scheduled_at: datetime
    location: Optional[str] = None
    description: Optional[str] = None
    agenda_text: Optional[str] = None
    participant_emails: List[str]
    duration_minutes: int = 60


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None
    agenda_text: Optional[str] = None
    duration_minutes: Optional[int] = None


class ParticipantResponse(BaseModel):
    id: UUID
    email: str
    name: Optional[str] = None
    role: str
    attendance_status: str

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

        return {
            "id": data.id,
            "email": data.email,
            "name": name,
            "role": role,
            "attendance_status": attendance_status
        }


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

    @model_validator(mode='before')
    @classmethod
    def extract_fields(cls, data: Any) -> Any:
        if isinstance(data, dict):
            return data
            
        status = data.status.value if hasattr(data.status, 'value') else data.status
        
        participant_count = len(data.participants) if hasattr(data, 'participants') else 0
        attendance_count = sum(1 for p in (data.participants if hasattr(data, 'participants') else []) if p.attendance and p.attendance.status.value == "hadir")
        
        has_recording = data.recording is not None if hasattr(data, 'recording') else False
        processing_status = getattr(data.recording, 'processing_status', None) if has_recording else None
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
            "processing_status": processing_status
        }


class MeetingListResponse(BaseModel):
    items: List[MeetingListItem]
    total: int
    page: int
    limit: int


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
    description: Optional[str] = None
    agenda_text: Optional[str] = None
    status: str
    duration_minutes: int
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
            
        status = data.status.value if hasattr(data.status, 'value') else data.status
        
        # If the recording object exists, it might have a processing_status
        has_recording = data.recording is not None if hasattr(data, 'recording') else False
        processing_status = getattr(data.recording, 'processing_status', None) if has_recording else None
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
            "description": data.description,
            "agenda_text": data.agenda_text,
            "status": status,
            "duration_minutes": data.duration_minutes,
            "organizer": data.organizer,
            "participants": data.participants,
            "recording": data.recording,
            "processing_status": processing_status,
            "transcript": transcript,
            "summary": summary,
            "action_items": action_items,
        }
