import uuid
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.database import Base


class AttendanceStatus(str, enum.Enum):
    pending = "pending"
    hadir = "hadir"
    tidak_hadir = "tidak_hadir"


class AttendanceMethod(str, enum.Enum):
    manual = "manual"
    link = "link"


class Attendance(Base):
    __tablename__ = "attendances"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    participant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meeting_participants.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    status: Mapped[AttendanceStatus] = mapped_column(
        SAEnum(AttendanceStatus, name="attendancestatus"),
        default=AttendanceStatus.pending,
        nullable=False,
    )
    checked_in_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    method: Mapped[AttendanceMethod | None] = mapped_column(
        SAEnum(AttendanceMethod, name="attendancemethod"), nullable=True
    )

    participant: Mapped["MeetingParticipant"] = relationship(
        "MeetingParticipant", back_populates="attendance"
    )
