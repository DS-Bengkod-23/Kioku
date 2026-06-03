import uuid
from datetime import datetime, timezone
from sqlalchemy import String, DateTime, Float, BigInteger, Text, ForeignKey, Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
import enum
from app.database import Base


class ProcessingStatus(str, enum.Enum):
    queued = "queued"
    transcribing = "transcribing"
    diarizing = "diarizing"
    extracting = "extracting"
    sending_email = "sending_email"
    completed = "completed"
    failed = "failed"


class Recording(Base):
    __tablename__ = "recordings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    file_url: Mapped[str] = mapped_column(String(1000), nullable=False)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    uploaded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        SAEnum(ProcessingStatus, name="processingstatus"),
        default=ProcessingStatus.queued,
        nullable=False,
    )
    processing_steps: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="recording")
