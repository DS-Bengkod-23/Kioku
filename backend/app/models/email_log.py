import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID
import enum
from app.database import Base


class EmailType(str, enum.Enum):
    invitation = "invitation"
    distribution = "distribution"


class EmailStatus(str, enum.Enum):
    sent = "sent"
    failed = "failed"


class EmailLog(Base):
    __tablename__ = "email_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    recipient: Mapped[str] = mapped_column(String(255), nullable=False)
    type: Mapped[EmailType] = mapped_column(
        SAEnum(EmailType, name="emailtype"), nullable=False
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    sent_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    status: Mapped[EmailStatus] = mapped_column(
        SAEnum(EmailStatus, name="emailstatus"), nullable=False
    )

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="email_logs")
