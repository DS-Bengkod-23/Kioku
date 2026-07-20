from datetime import datetime, timezone

from app.models.audit_log import AuditAction, AuditLog
from app.models.meeting import Meeting
from app.models.recording import Recording
from app.models.summary import Summary
from app.models.transcript import Transcript
from app.models.user import UserRole
from app.services import admin as admin_service


def _make_meeting_with_content(db_session, organizer):
    meeting = Meeting(
        organizer_id=organizer.id,
        title="Confidential Meeting",
        scheduled_at=datetime.now(timezone.utc),
    )
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)

    db_session.add(Transcript(meeting_id=meeting.id, segments=[{"speaker": "A", "text": "hello"}]))
    db_session.add(Summary(meeting_id=meeting.id, tldr="Discussed things", decisions=["Ship it"], topics=["planning"]))
    db_session.add(
        Recording(
            meeting_id=meeting.id,
            file_url="https://minio.internal/recordings/super-secret-audio.mp3",
            size=12345,
        )
    )
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


def test_request_access_returns_transcript_and_summary(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    organizer = make_user()
    meeting = _make_meeting_with_content(db_session, organizer)

    result = admin_service.request_meeting_content_access(db_session, admin, meeting.id, "investigating complaint")

    assert result.transcript_segments == [{"speaker": "A", "text": "hello"}]
    assert result.summary_tldr == "Discussed things"
    assert result.summary_decisions == ["Ship it"]


def test_request_access_never_exposes_recording_file_url(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    organizer = make_user()
    meeting = _make_meeting_with_content(db_session, organizer)

    result = admin_service.request_meeting_content_access(db_session, admin, meeting.id, "investigating complaint")

    assert not hasattr(result, "file_url")
    assert not hasattr(result, "recording")
    serialized = result.model_dump_json()
    assert "super-secret-audio" not in serialized
    assert "minio.internal" not in serialized


def test_request_access_writes_audit_log_with_reason(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    organizer = make_user()
    meeting = _make_meeting_with_content(db_session, organizer)

    admin_service.request_meeting_content_access(db_session, admin, meeting.id, "investigating complaint")

    log = db_session.query(AuditLog).filter(AuditLog.target_id == meeting.id).one()
    assert log.action == AuditAction.request_meeting_access
    assert log.actor_id == admin.id
    assert log.reason == "investigating complaint"


def test_repeated_requests_write_separate_audit_rows_not_a_persisted_grant(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    organizer = make_user()
    meeting = _make_meeting_with_content(db_session, organizer)

    admin_service.request_meeting_content_access(db_session, admin, meeting.id, "reason one")
    admin_service.request_meeting_content_access(db_session, admin, meeting.id, "reason two")

    logs = (
        db_session.query(AuditLog)
        .filter(AuditLog.target_id == meeting.id, AuditLog.action == AuditAction.request_meeting_access)
        .all()
    )
    assert len(logs) == 2
    assert {log.reason for log in logs} == {"reason one", "reason two"}


def test_regular_user_gets_403_on_access_request(client, make_user, auth_headers):
    user = make_user(role=UserRole.user)

    response = client.post(
        f"/api/v1/admin/meetings/{user.id}/access-requests",  # any UUID — 403 fires before the lookup
        json={"reason": "curious"},
        headers=auth_headers(user),
    )
    assert response.status_code == 403
