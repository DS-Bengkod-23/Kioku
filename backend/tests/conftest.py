import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Mirror alembic/env.py's defensive sys.path handling so `import app...`
# works regardless of how pytest is invoked (bare `pytest` vs `python -m pytest`).
_BACKEND_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_BACKEND_ROOT))

# Tests must never touch the dev database. Redirect DATABASE_URL to a sibling
# "_test" database *before* anything imports app.config, so the one Settings()
# singleton constructed for this whole test process only ever sees the test URL.
_raw_db_url = os.environ.get("DATABASE_URL", "postgresql://meetmate:meetmate@localhost:5432/meetmate")
_base_url, _, _db_name = _raw_db_url.rpartition("/")
_test_db_name = f"{_db_name}_test"
os.environ["DATABASE_URL"] = f"{_base_url}/{_test_db_name}"

import psycopg  # noqa: E402
import pytest  # noqa: E402
from alembic import command  # noqa: E402
from alembic.config import Config  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine, text  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402

from app.config import settings  # noqa: E402
from app.database import Base, _get_engine_url, get_db  # noqa: E402
from app.main import app  # noqa: E402
from app import models  # noqa: E402,F401 — registers every model on Base.metadata
from app.models.action_item import ActionItem, ActionItemSource  # noqa: E402
from app.models.invitation import Invitation  # noqa: E402
from app.models.meeting import Meeting, NotulenStatus  # noqa: E402
from app.models.participant import MeetingParticipant, ParticipantRole  # noqa: E402
from app.models.recording import ProcessingStatus, Recording  # noqa: E402
from app.models.summary import Summary  # noqa: E402
from app.models.transcript import Transcript  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.services.auth import create_access_token, hash_password  # noqa: E402

_ALEMBIC_INI = str(_BACKEND_ROOT / "alembic.ini")

_test_engine = create_engine(_get_engine_url(settings.DATABASE_URL))
_TestSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=_test_engine)


def _create_test_database_if_missing() -> None:
    # CREATE DATABASE can't run inside a transaction block, and psycopg (v3)
    # accepts the bare postgresql:// URL directly (unlike SQLAlchemy, which
    # needs the +psycopg driver suffix from _get_engine_url).
    with psycopg.connect(_raw_db_url, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (_test_db_name,))
            if cur.fetchone() is None:
                cur.execute(f'CREATE DATABASE "{_test_db_name}"')


def _migrate_test_database() -> None:
    # No explicit sqlalchemy.url here: alembic/env.py reads settings.DATABASE_URL
    # itself, which by this point already resolves to the test database.
    command.upgrade(Config(_ALEMBIC_INI), "head")


@pytest.fixture(scope="session", autouse=True)
def _test_database_ready():
    _create_test_database_if_missing()
    _migrate_test_database()
    yield


@pytest.fixture(autouse=True)
def _clean_tables():
    yield
    table_names = ", ".join(f'"{table.name}"' for table in Base.metadata.sorted_tables)
    with _test_engine.begin() as conn:
        conn.execute(text(f"TRUNCATE TABLE {table_names} RESTART IDENTITY CASCADE"))


@pytest.fixture
def db_session():
    session = _TestSessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    def _override_get_db():
        session = _TestSessionLocal()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_db] = _override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def make_user(db_session):
    def _make(role: UserRole = UserRole.user, email: str | None = None, password: str = "password123") -> User:
        user = User(
            email=email or f"{uuid.uuid4()}@example.com",
            name="Test User",
            password_hash=hash_password(password),
            role=role,
        )
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user

    return _make


@pytest.fixture
def make_meeting(db_session):
    """Meeting 'Team Sync' dengan organizer + member (peserta berundangan).

    `with_notulen` mengisi Summary/Transcript/ActionItem(ai, assignee = member
    pertama); `with_recording` menambah Recording yang sudah completed.
    """

    def _make(
        organizer: User,
        members: list[User] = (),
        *,
        notulen_status: NotulenStatus | None = None,
        with_notulen: bool = False,
        with_recording: bool = False,
    ) -> Meeting:
        now = datetime.now(timezone.utc)
        meeting = Meeting(
            organizer_id=organizer.id,
            title="Team Sync",
            scheduled_at=now + timedelta(days=1),
            notulen_status=notulen_status,
        )
        db_session.add(meeting)
        db_session.flush()

        db_session.add(
            MeetingParticipant(
                meeting_id=meeting.id,
                user_id=organizer.id,
                email=organizer.email,
                role=ParticipantRole.organizer,
            )
        )
        member_participants = []
        for member in members:
            participant = MeetingParticipant(
                meeting_id=meeting.id,
                user_id=member.id,
                email=member.email,
                role=ParticipantRole.peserta,
            )
            participant.invitation = Invitation(
                token=uuid.uuid4().hex, expires_at=now + timedelta(days=30)
            )
            db_session.add(participant)
            member_participants.append(participant)
        db_session.flush()

        if with_notulen:
            db_session.add(
                Summary(
                    meeting_id=meeting.id,
                    tldr="Ringkasan AI",
                    decisions=["Keputusan A"],
                    topics=["Topik A"],
                )
            )
            db_session.add(
                Transcript(
                    meeting_id=meeting.id,
                    segments=[
                        {"speaker": "SPEAKER_00", "start": 0.0, "end": 5.0, "text": "Halo semua"}
                    ],
                )
            )
            db_session.add(
                ActionItem(
                    meeting_id=meeting.id,
                    task="Kirim laporan",
                    source=ActionItemSource.ai,
                    assignee_participant_id=(
                        member_participants[0].id if member_participants else None
                    ),
                )
            )
        if with_recording:
            db_session.add(
                Recording(
                    meeting_id=meeting.id,
                    file_url="meetings/x.mp3",
                    size=1,
                    processing_status=ProcessingStatus.completed,
                )
            )
        db_session.commit()
        db_session.refresh(meeting)
        return meeting

    return _make


@pytest.fixture
def auth_headers():
    def _headers(user: User) -> dict[str, str]:
        token = create_access_token({"sub": str(user.id)})
        return {"Authorization": f"Bearer {token}"}

    return _headers
