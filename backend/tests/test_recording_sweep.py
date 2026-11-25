import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from app.config import settings
from app.models.recording import Recording
from app.models.recording_session import RecordingSession
from app.models.user import User
from app.services.recording_session import contiguous_prefix_length
from app.tasks.recording_session import finalize_recording_session_task, sweep_recording_sessions_task
from app.worker import celery_app

TINY_M4A = Path(__file__).resolve().parent / "fixtures" / "tiny.m4a"


def _base(meeting_id) -> str:
    return f"/api/v1/meetings/{meeting_id}/recording/sessions"


@pytest.fixture
def finalize_delays(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.tasks.recording_session.finalize_recording_session_task.delay", lambda *args: calls.append(args)
    )
    return calls


@pytest.fixture
def pipeline_delays(monkeypatch):
    calls = []
    monkeypatch.setattr(
        "app.tasks.process_recording.process_recording_task.delay", lambda *args: calls.append(args)
    )
    return calls


@pytest.fixture
def new_session(client, db_session, make_user, make_meeting, auth_headers, fake_storage):
    """Membuat sesi dengan potongan di indeks tertentu, lalu 'menuanya'."""
    organizer = make_user()

    def _make(indices, *, idle_minutes: float = 60, status: str | None = None, finished_hours_ago: float | None = None):
        meeting = make_meeting(organizer)
        headers = auth_headers(organizer)
        session_id = client.post(_base(meeting.id), headers=headers, json={"mime_type": "audio/webm"}).json()["session_id"]
        for index in indices:
            response = client.put(
                f"{_base(meeting.id)}/{session_id}/chunks/{index}",
                headers={**headers, "Content-Type": "application/octet-stream"},
                content=f"chunk-{index}".encode(),
            )
            assert response.status_code == 200
        session = db_session.get(RecordingSession, uuid.UUID(session_id))
        session.last_activity_at = datetime.now(timezone.utc) - timedelta(minutes=idle_minutes)
        if status:
            session.status = status
        if finished_hours_ago is not None:
            session.finished_at = datetime.now(timezone.utc) - timedelta(hours=finished_hours_ago)
        db_session.commit()
        return meeting, session_id

    return _make


def _reload(db_session, session_id) -> RecordingSession:
    db_session.expire_all()
    return db_session.get(RecordingSession, uuid.UUID(session_id))


def _chunks_in_storage(fake_storage):
    return sorted(key for key in fake_storage.objects if key.startswith("recording-sessions/"))


# ------------------------------------------------- aturan potongan berurutan


@pytest.mark.parametrize(
    "indices,expected",
    [
        ([], 0),
        ([0], 1),
        ([0, 1, 2], 3),
        ([0, 1, 3], 2),
        ([1, 2, 3], 0),
        ([2, 0, 1], 3),
        ([0, 1, 1, 2], 3),
        ({0, 1, 2, 4, 5}, 3),
    ],
)
def test_contiguous_prefix_length_stops_at_first_gap(indices, expected):
    assert contiguous_prefix_length(indices) == expected


# --------------------------------------------------------- sesi terlantar


def test_idle_session_with_contiguous_chunks_is_finalized(db_session, new_session, finalize_delays):
    meeting, session_id = new_session([0, 1, 2], idle_minutes=30)

    sweep_recording_sessions_task()

    session = _reload(db_session, session_id)
    assert session.status == "finalizing"
    assert session.chunk_count == 3
    assert finalize_delays == [(session_id,)]


def test_chunks_after_a_gap_are_left_out_of_the_recording(
    db_session, new_session, fake_storage, fake_converter, pipeline_delays, finalize_delays
):
    meeting, session_id = new_session([0, 1, 3], idle_minutes=30)

    sweep_recording_sessions_task()
    assert _reload(db_session, session_id).chunk_count == 2
    finalize_recording_session_task(session_id)  # worker memprosesnya

    # Menggabung potongan yang bolong bisa merusak berkas, jadi potongan 3 tidak ikut.
    assert fake_converter.inputs == [b"chunk-0chunk-1"]
    assert _reload(db_session, session_id).status == "finalized"
    assert db_session.query(Recording).filter_by(meeting_id=meeting.id).count() == 1
    assert _chunks_in_storage(fake_storage) == []  # termasuk potongan 3
    assert len(pipeline_delays) == 1


def test_idle_session_without_chunks_is_discarded(db_session, new_session, finalize_delays):
    meeting, session_id = new_session([], idle_minutes=30)

    sweep_recording_sessions_task()

    session = _reload(db_session, session_id)
    assert session.status == "abandoned"
    assert session.finished_at is not None
    assert finalize_delays == []


def test_idle_session_whose_first_chunk_never_arrived_is_discarded_with_its_chunks(
    db_session, new_session, fake_storage, finalize_delays
):
    meeting, session_id = new_session([2, 3], idle_minutes=30)

    sweep_recording_sessions_task()

    assert _reload(db_session, session_id).status == "abandoned"
    assert _chunks_in_storage(fake_storage) == []
    assert finalize_delays == []


def test_a_discarded_session_no_longer_blocks_a_new_recording(client, db_session, new_session, auth_headers, finalize_delays):
    meeting, session_id = new_session([], idle_minutes=30)
    sweep_recording_sessions_task()
    organizer = db_session.get(User, meeting.organizer_id)

    response = client.post(_base(meeting.id), headers=auth_headers(organizer), json={"mime_type": "audio/webm"})

    assert response.status_code == 201


def test_active_session_is_left_alone(db_session, new_session, finalize_delays, monkeypatch):
    monkeypatch.setattr(settings, "RECORDING_SESSION_ABANDON_MINUTES", 10)
    meeting, recent = new_session([0, 1], idle_minutes=5)
    meeting_2, stale = new_session([0, 1], idle_minutes=11)

    sweep_recording_sessions_task()

    assert _reload(db_session, recent).status == "recording"
    assert _reload(db_session, stale).status == "finalizing"
    assert finalize_delays == [(stale,)]


@pytest.mark.parametrize("status", ["finalized", "failed", "abandoned"])
def test_only_recording_sessions_are_swept_for_abandonment(db_session, new_session, finalize_delays, status):
    meeting, session_id = new_session([0, 1], idle_minutes=600, status=status, finished_hours_ago=0)

    sweep_recording_sessions_task()

    assert _reload(db_session, session_id).status == status
    assert finalize_delays == []


def test_sweeping_twice_queues_finalize_once(db_session, new_session, finalize_delays):
    meeting, session_id = new_session([0, 1], idle_minutes=30)

    sweep_recording_sessions_task()
    sweep_recording_sessions_task()

    assert finalize_delays == [(session_id,)]


# --------------------------------------------- sesi macet di `finalizing`


def test_finalizing_session_stuck_past_the_limit_is_queued_again(db_session, new_session, finalize_delays, monkeypatch):
    monkeypatch.setattr(settings, "RECORDING_FINALIZE_STALE_MINUTES", 30)
    meeting, session_id = new_session([0, 1, 2], idle_minutes=31, status="finalizing")
    before = _reload(db_session, session_id).last_activity_at

    sweep_recording_sessions_task()

    session = _reload(db_session, session_id)
    assert finalize_delays == [(session_id,)]
    assert session.status == "finalizing"  # task finalize yang mengubahnya, bukan sweep
    assert session.chunk_count == 3
    assert session.last_activity_at > before  # jam macet dimulai ulang


def test_finalizing_session_within_the_limit_is_left_alone(db_session, new_session, finalize_delays, monkeypatch):
    monkeypatch.setattr(settings, "RECORDING_FINALIZE_STALE_MINUTES", 30)
    meeting, session_id = new_session([0, 1], idle_minutes=29, status="finalizing")

    sweep_recording_sessions_task()

    assert finalize_delays == []
    assert _reload(db_session, session_id).status == "finalizing"


def test_stuck_finalizing_session_is_queued_only_once_per_window(db_session, new_session, finalize_delays, monkeypatch):
    monkeypatch.setattr(settings, "RECORDING_FINALIZE_STALE_MINUTES", 30)
    meeting, session_id = new_session([0, 1], idle_minutes=45, status="finalizing")

    sweep_recording_sessions_task()
    sweep_recording_sessions_task()

    assert finalize_delays == [(session_id,)]


def test_stuck_finalizing_session_is_recovered_end_to_end(
    db_session, new_session, fake_storage, fake_converter, pipeline_delays, finalize_delays, monkeypatch
):
    monkeypatch.setattr(settings, "RECORDING_FINALIZE_STALE_MINUTES", 30)
    meeting, session_id = new_session([0, 1], idle_minutes=45, status="finalizing")

    sweep_recording_sessions_task()
    finalize_recording_session_task(session_id)  # worker yang baru menjalankannya

    assert _reload(db_session, session_id).status == "finalized"
    assert db_session.query(Recording).filter_by(meeting_id=meeting.id).count() == 1
    assert len(pipeline_delays) == 1
    assert _chunks_in_storage(fake_storage) == []


@pytest.mark.parametrize("status", ["recording", "finalized", "failed", "abandoned"])
def test_only_finalizing_sessions_are_requeued_as_stuck(db_session, new_session, finalize_delays, monkeypatch, status):
    monkeypatch.setattr(settings, "RECORDING_FINALIZE_STALE_MINUTES", 30)
    monkeypatch.setattr(settings, "RECORDING_SESSION_ABANDON_MINUTES", 100000)  # `recording` tidak ikut disapu
    monkeypatch.setattr(settings, "RECORDING_FAILED_RETENTION_HOURS", 100000)
    meeting, session_id = new_session([0, 1], idle_minutes=600, status=status, finished_hours_ago=0)

    sweep_recording_sessions_task()

    assert finalize_delays == []
    assert _reload(db_session, session_id).status == status


# ------------------------------------------------- pembersihan sesi gagal


def test_failed_session_past_retention_loses_its_chunks(db_session, new_session, fake_storage, monkeypatch):
    monkeypatch.setattr(settings, "RECORDING_FAILED_RETENTION_HOURS", 24)
    meeting, session_id = new_session([0, 1, 2], status="failed", finished_hours_ago=25, idle_minutes=0)

    sweep_recording_sessions_task()

    assert _chunks_in_storage(fake_storage) == []
    # Tanpa potongan, sesi tidak bisa dicoba ulang; ditandai dibuang agar tidak dipindai lagi.
    assert _reload(db_session, session_id).status == "abandoned"


def test_failed_session_within_retention_keeps_its_chunks(db_session, new_session, fake_storage, monkeypatch):
    monkeypatch.setattr(settings, "RECORDING_FAILED_RETENTION_HOURS", 24)
    meeting, session_id = new_session([0, 1, 2], status="failed", finished_hours_ago=23, idle_minutes=0)

    sweep_recording_sessions_task()

    assert len(_chunks_in_storage(fake_storage)) == 3
    assert _reload(db_session, session_id).status == "failed"


def test_cleanup_only_removes_the_expired_sessions_chunks(db_session, new_session, fake_storage, monkeypatch):
    monkeypatch.setattr(settings, "RECORDING_FAILED_RETENTION_HOURS", 24)
    new_session([0, 1], status="failed", finished_hours_ago=48, idle_minutes=0)
    meeting, keep_id = new_session([0, 1, 2], status="failed", finished_hours_ago=1, idle_minutes=0)

    sweep_recording_sessions_task()

    assert len(_chunks_in_storage(fake_storage)) == 3
    assert _reload(db_session, keep_id).status == "failed"


# ------------------------------------------------------------- penjadwalan


def test_sweep_is_scheduled_by_celery_beat_at_the_configured_interval():
    entries = [
        entry
        for entry in celery_app.conf.beat_schedule.values()
        if entry["task"] == "app.tasks.recording_session.sweep_recording_sessions_task"
    ]

    assert len(entries) == 1
    assert entries[0]["schedule"] == settings.RECORDING_SWEEP_INTERVAL_MINUTES * 60


def test_sweep_task_is_registered_with_celery():
    assert "app.tasks.recording_session.sweep_recording_sessions_task" in celery_app.tasks
