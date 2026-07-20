import os
import sys
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
