import uuid
from typing import Optional
from pydantic import BaseModel
from datetime import datetime, date
from app.models.attendance import AttendanceStatus, AttendanceMethod
from app.models.action_item import ActionItemStatus


class CheckinSummary(BaseModel):
    tldr: str
    decisions: list[str]
    topics: list[str]


class CheckinActionItem(BaseModel):
    id: uuid.UUID
    task: str
    due_date: date | None
    status: str  # "open" | "done"


class CheckinPageResponse(BaseModel):
    meeting_id: uuid.UUID
    meeting_title: str
    scheduled_at: datetime
    location: str | None = None
    participant_name: str
    already_checked_in: bool
    attendance_locked: bool = False
    processing_status: Optional[str] = None
    summary: Optional[dict] = None
    action_items: list[dict] = []


class CheckinActionItemUpdateRequest(BaseModel):
    status: ActionItemStatus


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


class ActionItemStatusUpdate(BaseModel):
    status: str  # "open" | "done"
