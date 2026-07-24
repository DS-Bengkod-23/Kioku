from uuid import UUID
from datetime import datetime
from pydantic import BaseModel
from app.models.user import UserRole
from app.models.meeting import MeetingStatus
from app.models.participant import ParticipantRole
from app.models.attendance import AttendanceStatus
from app.models.audit_log import AuditAction


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


class MeetingContentAccessRequest(BaseModel):
    reason: str


class AuditLogResponse(BaseModel):
    id: UUID
    actor_id: UUID | None
    actor_name: str | None = None
    actor_email: str | None = None
    action: AuditAction
    target_type: str
    target_id: UUID
    reason: str | None
    created_at: datetime

    model_config = {"from_attributes": True}


class MeetingContentAccessResponse(BaseModel):
    meeting_id: UUID
    # Deliberately no audio/recording field anywhere on this model — the
    # raw recording is permanently off-limits to admin access, regardless
    # of role. Never add one here.
    transcript_segments: list | None = None
    summary_tldr: str | None = None
    summary_decisions: list | None = None
    summary_topics: list | None = None
