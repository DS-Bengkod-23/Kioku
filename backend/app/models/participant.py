import uuid
from sqlalchemy import String, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.database import Base


class ParticipantRole(str, enum.Enum):
    organizer = "organizer"
    peserta = "peserta"


class MeetingParticipant(Base):
    __tablename__ = "meeting_participants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[ParticipantRole] = mapped_column(
        SAEnum(ParticipantRole, name="participantrole"), nullable=False
    )

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="participants")
    user: Mapped["User | None"] = relationship("User", back_populates="participations")
    invitation: Mapped["Invitation | None"] = relationship(
        "Invitation", back_populates="participant", uselist=False, cascade="all, delete-orphan"
    )
    attendance: Mapped["Attendance | None"] = relationship(
        "Attendance", back_populates="participant", uselist=False, cascade="all, delete-orphan"
    )
    assigned_action_items: Mapped[list["ActionItem"]] = relationship(
        "ActionItem", back_populates="assignee_participant", foreign_keys="ActionItem.assignee_participant_id"
    )
