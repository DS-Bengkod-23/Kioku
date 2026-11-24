from datetime import datetime, timezone

from app.models.meeting import Meeting, NotulenStatus
from app.models.notulen_version import NotulenVersion, NotulenVersionKind
from app.models.recording import Recording
from app.models.summary import Summary
from app.models.action_item import ActionItem
from app.models.transcript import Transcript
from app.services import recording as recording_service


def _published_meeting(make_user, make_meeting):
    organizer = make_user()
    meeting = make_meeting(
        organizer,
        [make_user()],
        with_notulen=True,
        with_recording=True,
        notulen_status=NotulenStatus.published,
    )
    return organizer, meeting


def test_delete_recording_keeps_published_notulen(
    client, db_session, make_user, make_meeting, auth_headers, monkeypatch
):
    organizer, meeting = _published_meeting(make_user, make_meeting)
    deleted_files = []
    monkeypatch.setattr("app.services.storage.delete_file", deleted_files.append)

    response = client.delete(
        f"/api/v1/meetings/{meeting.id}/recording", headers=auth_headers(organizer)
    )

    assert response.status_code == 204
    assert deleted_files == ["meetings/x.mp3"]
    db_session.expire_all()
    assert db_session.query(Recording).filter_by(meeting_id=meeting.id).count() == 0
    assert db_session.query(Summary).filter_by(meeting_id=meeting.id).count() == 1
    assert db_session.query(Transcript).filter_by(meeting_id=meeting.id).count() == 1
    assert db_session.query(ActionItem).filter_by(meeting_id=meeting.id).count() == 1
    assert db_session.get(Meeting, meeting.id).notulen_status == NotulenStatus.published


def test_clear_previous_processing_resets_status_keeps_versions(
    db_session, make_user, make_meeting
):
    _, meeting = _published_meeting(make_user, make_meeting)
    db_session.add(
        NotulenVersion(
            meeting_id=meeting.id,
            kind=NotulenVersionKind.published,
            version=1,
            content={},
        )
    )
    meeting.notulen_edited_at = datetime.now(timezone.utc)
    db_session.commit()

    recording_service._clear_previous_processing(db_session, meeting.recording, meeting)
    db_session.commit()

    db_session.expire_all()
    meeting = db_session.get(Meeting, meeting.id)
    assert meeting.notulen_status is None
    assert meeting.notulen_edited_at is None
    assert db_session.query(Summary).filter_by(meeting_id=meeting.id).count() == 0
    assert db_session.query(Recording).filter_by(meeting_id=meeting.id).count() == 0
    versions = db_session.query(NotulenVersion).filter_by(meeting_id=meeting.id).all()
    assert [v.version for v in versions] == [1]
