from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.models.user import UserRole
from app.models.meeting import MeetingStatus
from app.models.participant import ParticipantRole
from app.models.attendance import AttendanceStatus


class UserAdminResponse(BaseModel):
    id: UUID
    name: str
    email: str
    role: UserRole
    suspended_at: datetime | None = None
    created_at: datetime

    model_config = {"from_attributes": True}


class UserRoleUpdateRequest(BaseModel):
    role: UserRole


class ParticipantAdminResponse(BaseModel):
    name: str
    email: str
    role: ParticipantRole
    attendance_status: AttendanceStatus | None = None


class ActionItemsSummary(BaseModel):
    open: int
    done: int


class MeetingAdminResponse(BaseModel):
    id: UUID
    title: str
    scheduled_at: datetime
    status: MeetingStatus
    organizer_name: str
    organizer_email: str
    participants: list[ParticipantAdminResponse]
    action_items: ActionItemsSummary
