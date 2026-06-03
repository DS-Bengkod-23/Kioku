import uuid
from sqlalchemy import Text, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB
from app.database import Base


class Summary(Base):
    __tablename__ = "summaries"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    tldr: Mapped[str] = mapped_column(Text, nullable=False)
    decisions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    topics: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)

    meeting: Mapped["Meeting"] = relationship("Meeting", back_populates="summary")
