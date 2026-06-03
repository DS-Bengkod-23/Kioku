from pydantic import BaseModel, ConfigDict, model_validator
from typing import List, Optional, Any
from datetime import datetime
from uuid import UUID


class MeetingCreate(BaseModel):
    title: str
    scheduled_at: datetime
    location: Optional[str] = None
    description: Optional[str] = None
    agenda_text: Optional[str] = None
    participant_emails: List[str]


class MeetingUpdate(BaseModel):
    title: Optional[str] = None
    scheduled_at: Optional[datetime] = None
    location: Optional[str] = None
    description: Optional[str] = None
    agenda_text: Optional[str] = None


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
    organizer: OrganizerResponse
    participants: List[ParticipantResponse]
    recording: Optional[Any] = None
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

        return {
            "id": data.id,
            "title": data.title,
            "scheduled_at": data.scheduled_at,
            "location": data.location,
            "description": data.description,
            "agenda_text": data.agenda_text,
            "status": status,
            "organizer": data.organizer,
            "participants": data.participants,
            "recording": data.recording,
            "processing_status": processing_status,
            "transcript": data.transcript,
            "summary": data.summary,
            "action_items": data.action_items,
        }
