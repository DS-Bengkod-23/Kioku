import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum as SAEnum, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


class NotulenVersionKind(str, enum.Enum):
    ai = "ai"
    published = "published"


class NotulenVersion(Base):
    """Snapshot notulen: `published` (bernomor, tiap kirim) atau `ai` (output ML asli)."""

    __tablename__ = "notulen_versions"
    # NULL version (kind=ai) tidak saling bentrok di unique constraint Postgres.
    __table_args__ = (
        UniqueConstraint("meeting_id", "version", name="uq_notulen_versions_meeting_version"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("meetings.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    kind: Mapped[NotulenVersionKind] = mapped_column(
        SAEnum(NotulenVersionKind, name="notulenversionkind"), nullable=False
    )
    version: Mapped[int | None] = mapped_column(Integer, nullable=True)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    created_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False
    )

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="notulen_versions")
