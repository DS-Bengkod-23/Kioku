import uuid
from datetime import date
from sqlalchemy import Text, Date, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.database import Base


class ActionItemStatus(str, enum.Enum):
    open = "open"
    done = "done"


class ActionItem(Base):
    __tablename__ = "action_items"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    task: Mapped[str] = mapped_column(Text, nullable=False)
    assignee_participant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meeting_participants.id", ondelete="SET NULL"),
        nullable=True,
    )
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    status: Mapped[ActionItemStatus] = mapped_column(
        SAEnum(ActionItemStatus, name="actionitemstatus"),
        default=ActionItemStatus.open,
        nullable=False,
    )

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="action_items")
    assignee_participant: Mapped["MeetingParticipant | None"] = relationship(
        "MeetingParticipant",
        back_populates="assigned_action_items",
        foreign_keys=[assignee_participant_id],
    )
