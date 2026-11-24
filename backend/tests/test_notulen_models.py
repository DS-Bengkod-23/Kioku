import pytest
from sqlalchemy.exc import IntegrityError

from app.models.meeting import Meeting
from app.models.notulen_version import NotulenVersion, NotulenVersionKind


def test_published_version_number_unique_per_meeting(db_session, make_user, make_meeting):
    meeting = make_meeting(make_user())
    for _ in range(2):
        db_session.add(
            NotulenVersion(
                meeting_id=meeting.id,
                kind=NotulenVersionKind.published,
                version=1,
                content={},
            )
        )
    with pytest.raises(IntegrityError):
        db_session.commit()


def test_multiple_ai_snapshots_allowed(db_session, make_user, make_meeting):
    meeting = make_meeting(make_user())
    for _ in range(2):
        db_session.add(
            NotulenVersion(
                meeting_id=meeting.id,
                kind=NotulenVersionKind.ai,
                version=None,
                content={},
            )
        )
    db_session.commit()
    db_session.refresh(meeting)
    assert len(meeting.notulen_versions) == 2


def test_deleting_meeting_cascades_versions(db_session, make_user, make_meeting):
    meeting = make_meeting(make_user())
    db_session.add(
        NotulenVersion(
            meeting_id=meeting.id,
            kind=NotulenVersionKind.published,
            version=1,
            content={},
        )
    )
    db_session.commit()

    db_session.delete(db_session.get(Meeting, meeting.id))
    db_session.commit()

    assert db_session.query(NotulenVersion).count() == 0
