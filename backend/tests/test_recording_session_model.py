import pytest
from sqlalchemy.exc import IntegrityError

from app.models.recording_session import RecordingSession, RecordingSessionStatus


def _session(meeting, user, status: str = "recording") -> RecordingSession:
    return RecordingSession(
        meeting_id=meeting.id,
        user_id=user.id,
        mime_type="audio/webm",
        status=status,
    )


def test_new_session_has_defaults(db_session, make_user, make_meeting):
    organizer = make_user()
    meeting = make_meeting(organizer)

    session = RecordingSession(meeting_id=meeting.id, user_id=organizer.id, mime_type="audio/webm")
    db_session.add(session)
    db_session.commit()
    db_session.refresh(session)

    assert session.status == "recording"
    assert session.chunk_count == 0
    assert session.last_activity_at is not None
    assert session.created_at is not None
    assert session.finished_at is None
    assert session.error_message is None


@pytest.mark.parametrize(
    "first,second",
    [
        ("recording", "recording"),
        ("recording", "finalizing"),
        ("finalizing", "recording"),
        ("finalizing", "finalizing"),
    ],
)
def test_database_rejects_two_active_sessions_for_same_meeting(
    db_session, make_user, make_meeting, first, second
):
    organizer = make_user()
    meeting = make_meeting(organizer)
    db_session.add(_session(meeting, organizer, first))
    db_session.commit()

    db_session.add(_session(meeting, organizer, second))
    with pytest.raises(IntegrityError):
        db_session.commit()


@pytest.mark.parametrize("finished_status", ["failed", "finalized", "abandoned"])
def test_finished_sessions_do_not_block_a_new_active_session(
    db_session, make_user, make_meeting, finished_status
):
    organizer = make_user()
    meeting = make_meeting(organizer)
    db_session.add(_session(meeting, organizer, finished_status))
    db_session.add(_session(meeting, organizer, finished_status))
    db_session.commit()

    db_session.add(_session(meeting, organizer, "recording"))
    db_session.commit()

    assert db_session.query(RecordingSession).filter_by(meeting_id=meeting.id).count() == 3


def test_active_sessions_for_different_meetings_do_not_conflict(db_session, make_user, make_meeting):
    organizer = make_user()
    meeting_a = make_meeting(organizer)
    meeting_b = make_meeting(organizer)

    db_session.add(_session(meeting_a, organizer))
    db_session.add(_session(meeting_b, organizer))
    db_session.commit()

    assert db_session.query(RecordingSession).count() == 2


def test_status_enum_values_match_the_api_contract():
    # Nilai ini adalah kontrak dengan frontend (GET .../sessions/{id}) dan disimpan
    # sebagai teks biasa di kolom status, jadi harus persis sama dengan spec.
    assert {status.value for status in RecordingSessionStatus} == {
        "recording",
        "finalizing",
        "finalized",
        "failed",
        "abandoned",
    }


def test_deleting_meeting_removes_its_sessions(db_session, make_user, make_meeting):
    organizer = make_user()
    meeting = make_meeting(organizer)
    db_session.add(_session(meeting, organizer))
    db_session.commit()

    db_session.delete(meeting)
    db_session.commit()

    assert db_session.query(RecordingSession).count() == 0
