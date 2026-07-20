from datetime import datetime, timezone

from app.models.audit_log import AuditAction, AuditLog
from app.models.meeting import Meeting
from app.models.participant import MeetingParticipant, ParticipantRole
from app.models.recording import Recording
from app.models.user import UserRole
from app.services import admin as admin_service


def _make_meeting(db_session, organizer, with_recording=False):
    meeting = Meeting(organizer_id=organizer.id, title="Team Sync", scheduled_at=datetime.now(timezone.utc))
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)

    db_session.add(
        MeetingParticipant(
            meeting_id=meeting.id,
            user_id=organizer.id,
            email=organizer.email,
            role=ParticipantRole.organizer,
        )
    )
    if with_recording:
        db_session.add(Recording(meeting_id=meeting.id, file_url="https://minio/x.mp3", size=1))
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


def test_admin_can_soft_delete_meeting(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    organizer = make_user()
    meeting = _make_meeting(db_session, organizer)

    admin_service.delete_meeting(db_session, admin, meeting.id)

    db_session.refresh(meeting)
    assert meeting.deleted_at is not None
    assert meeting.deleted_by_admin_id == admin.id


def test_deleting_already_deleted_meeting_is_noop(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    organizer = make_user()
    meeting = _make_meeting(db_session, organizer)

    admin_service.delete_meeting(db_session, admin, meeting.id)
    admin_service.delete_meeting(db_session, admin, meeting.id)

    logs = (
        db_session.query(AuditLog)
        .filter(AuditLog.target_id == meeting.id, AuditLog.action == AuditAction.delete_meeting)
        .all()
    )
    assert len(logs) == 1


def test_delete_meeting_writes_audit_log(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    organizer = make_user()
    meeting = _make_meeting(db_session, organizer)

    admin_service.delete_meeting(db_session, admin, meeting.id)

    log = db_session.query(AuditLog).filter(AuditLog.target_id == meeting.id).one()
    assert log.action == AuditAction.delete_meeting
    assert log.actor_id == admin.id


def test_participant_sees_generic_notice_for_deleted_meeting(client, db_session, make_user, auth_headers):
    admin = make_user(role=UserRole.admin)
    organizer = make_user()
    meeting = _make_meeting(db_session, organizer)

    admin_service.delete_meeting(db_session, admin, meeting.id)

    response = client.get(f"/api/v1/meetings/{meeting.id}", headers=auth_headers(organizer))
    assert response.status_code == 200
    body = response.json()
    assert body["deleted"] is True
    assert "message" in body
    assert "participants" not in body


def test_admin_can_soft_delete_recording(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    organizer = make_user()
    meeting = _make_meeting(db_session, organizer, with_recording=True)
    recording = db_session.query(Recording).filter(Recording.meeting_id == meeting.id).one()

    admin_service.delete_recording(db_session, admin, recording.id)

    db_session.refresh(recording)
    assert recording.deleted_at is not None
    assert recording.deleted_by_admin_id == admin.id


def test_deleted_recording_hidden_from_meeting_detail(client, db_session, make_user, auth_headers):
    admin = make_user(role=UserRole.admin)
    organizer = make_user()
    meeting = _make_meeting(db_session, organizer, with_recording=True)
    recording = db_session.query(Recording).filter(Recording.meeting_id == meeting.id).one()

    admin_service.delete_recording(db_session, admin, recording.id)

    response = client.get(f"/api/v1/meetings/{meeting.id}", headers=auth_headers(organizer))
    assert response.status_code == 200
    body = response.json()
    assert body["recording"] is None
    assert body["processing_status"] is None


def test_regular_user_gets_403_on_admin_delete_meeting(client, make_user, auth_headers):
    user = make_user(role=UserRole.user)
    response = client.delete(f"/api/v1/admin/meetings/{user.id}", headers=auth_headers(user))
    assert response.status_code == 403


def test_regular_user_gets_403_on_admin_delete_recording(client, make_user, auth_headers):
    user = make_user(role=UserRole.user)
    response = client.delete(f"/api/v1/admin/recordings/{user.id}", headers=auth_headers(user))
    assert response.status_code == 403
