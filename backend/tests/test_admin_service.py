from datetime import datetime, timezone

from app.models.user import User, UserRole
from app.models.meeting import Meeting, MeetingStatus
from app.models.participant import MeetingParticipant, ParticipantRole
from app.models.attendance import Attendance, AttendanceStatus
from app.models.action_item import ActionItem, ActionItemStatus
from app.services import admin as admin_service


def test_list_users_returns_role(db_session):
    admin = User(email="admin@example.com", name="Admin", password_hash="x", role=UserRole.admin)
    db_session.add(admin)
    db_session.commit()

    results = admin_service.list_users(db_session)
    assert len(results) == 1
    assert results[0].role == UserRole.admin


def test_list_meetings_metadata_aggregates_participants_and_action_items(db_session):
    organizer = User(email="organizer@example.com", name="Organizer", password_hash="x")
    db_session.add(organizer)
    db_session.commit()
    db_session.refresh(organizer)

    meeting = Meeting(
        organizer_id=organizer.id,
        title="Sprint Planning",
        scheduled_at=datetime.now(timezone.utc),
        status=MeetingStatus.completed,
    )
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)

    participant = MeetingParticipant(
        meeting_id=meeting.id,
        email="peserta@example.com",
        role=ParticipantRole.peserta,
    )
    db_session.add(participant)
    db_session.commit()
    db_session.refresh(participant)

    db_session.add(Attendance(participant_id=participant.id, status=AttendanceStatus.hadir))
    db_session.add_all(
        [
            ActionItem(meeting_id=meeting.id, task="Do thing", status=ActionItemStatus.open),
            ActionItem(meeting_id=meeting.id, task="Done thing", status=ActionItemStatus.done),
        ]
    )
    db_session.commit()

    results = admin_service.list_meetings_metadata(db_session)

    assert len(results) == 1
    result = results[0]
    assert result.title == "Sprint Planning"
    assert result.organizer_email == "organizer@example.com"
    assert len(result.participants) == 1
    assert result.participants[0].attendance_status == AttendanceStatus.hadir
    assert result.action_items.open == 1
    assert result.action_items.done == 1
