import uuid
from pydantic import BaseModel
from datetime import datetime
from app.models.attendance import AttendanceStatus, AttendanceMethod

class CheckinPageResponse(BaseModel):
    meeting_title: str
    scheduled_at: datetime
    location: str | None = None
    participant_name: str
    already_checked_in: bool

class CheckinConfirmResponse(BaseModel):
    message: str
    participant_name: str
    meeting_title: str

class AttendanceUpdateRequest(BaseModel):
    status: AttendanceStatus

class AttendanceUpdateResponse(BaseModel):
    participant_id: uuid.UUID
    name: str
    status: AttendanceStatus
    method: AttendanceMethod | None = None
