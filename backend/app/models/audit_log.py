import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.database import Base


class AuditAction(str, enum.Enum):
    suspend_user = "suspend_user"
    unsuspend_user = "unsuspend_user"
    promote_user = "promote_user"
    demote_user = "demote_user"
    reset_password = "reset_password"
    request_meeting_access = "request_meeting_access"
    delete_meeting = "delete_meeting"
    delete_recording = "delete_recording"


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    # Nullable + SET NULL (not CASCADE): the audit trail must survive even if
    # the actor's account is later removed — same reasoning as
    # MeetingParticipant.user_id.
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    action: Mapped[AuditAction] = mapped_column(
        SAEnum(AuditAction, name="auditaction"), nullable=False
    )
    # target_type/target_id are a polymorphic reference (user, meeting,
    # recording, ...) — deliberately not a FK.
    target_type: Mapped[str] = mapped_column(String(50), nullable=False)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    actor: Mapped["User"] = relationship("User")
