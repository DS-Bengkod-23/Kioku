import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class RecordingSessionStatus(str, enum.Enum):
    recording = "recording"
    finalizing = "finalizing"
    finalized = "finalized"
    failed = "failed"
    abandoned = "abandoned"


# Status yang menghitung sebagai "sesi aktif": hanya satu per meeting.
ACTIVE_STATUSES = (RecordingSessionStatus.recording.value, RecordingSessionStatus.finalizing.value)


def _now() -> datetime:
    return datetime.now(timezone.utc)


class RecordingSession(Base):
    """Sesi rekam langsung di browser: potongan audio masuk bertahap, lalu digabung
    oleh task finalize. `status` sengaja teks biasa (bukan enum PostgreSQL) supaya
    migrasi tidak terkena masalah tipe enum; nilainya lihat RecordingSessionStatus."""

    __tablename__ = "recording_sessions"
    __table_args__ = (
        # Aturan "satu sesi aktif per meeting" ditegakkan database, bukan hanya kode,
        # karena dua tab bisa memulai sesi bersamaan.
        Index(
            "uq_recording_sessions_active_per_meeting",
            "meeting_id",
            unique=True,
            postgresql_where=text("status IN ('recording', 'finalizing')"),
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    meeting_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("meetings.id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    mime_type: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=RecordingSessionStatus.recording.value
    )
    chunk_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    last_activity_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, default=_now)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
