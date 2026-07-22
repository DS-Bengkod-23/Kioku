import uuid
from datetime import datetime, timedelta, timezone

from app.models.invitation import Invitation
from app.models.meeting import Meeting
from app.models.participant import MeetingParticipant, ParticipantRole


def _make_meeting_with_participant(db_session, organizer, participant_user):
    meeting = Meeting(organizer_id=organizer.id, title="Team Sync", scheduled_at=datetime.now(timezone.utc))
    db_session.add(meeting)
    db_session.commit()
    db_session.refresh(meeting)

    db_session.add(
        MeetingParticipant(
            meeting_id=meeting.id, user_id=organizer.id, email=organizer.email, role=ParticipantRole.organizer,
        )
    )
    db_session.add(
        MeetingParticipant(
            meeting_id=meeting.id, user_id=participant_user.id, email=participant_user.email,
            role=ParticipantRole.peserta,
        )
    )
    db_session.commit()
    db_session.refresh(meeting)
    return meeting


def test_participant_can_confirm_attendance(client, db_session, make_user, auth_headers):
    organizer = make_user()
    participant = make_user()
    meeting = _make_meeting_with_participant(db_session, organizer, participant)

    response = client.patch(
        f"/api/v1/meetings/{meeting.id}/rsvp",
        json={"response": "akan_hadir"},
        headers=auth_headers(participant),
    )

    assert response.status_code == 200
    my_participant = next(p for p in response.json()["participants"] if p["email"] == participant.email)
    assert my_participant["rsvp_status"] == "akan_hadir"


def test_participant_can_decline_attendance(client, db_session, make_user, auth_headers):
    organizer = make_user()
    participant = make_user()
    meeting = _make_meeting_with_participant(db_session, organizer, participant)

    response = client.patch(
        f"/api/v1/meetings/{meeting.id}/rsvp",
        json={"response": "tidak_hadir"},
        headers=auth_headers(participant),
    )

    assert response.status_code == 200
    my_participant = next(p for p in response.json()["participants"] if p["email"] == participant.email)
    assert my_participant["rsvp_status"] == "tidak_hadir"


def test_default_rsvp_status_is_pending(client, db_session, make_user, auth_headers):
    organizer = make_user()
    participant = make_user()
    meeting = _make_meeting_with_participant(db_session, organizer, participant)

    response = client.get(f"/api/v1/meetings/{meeting.id}", headers=auth_headers(organizer))

    assert response.status_code == 200
    my_participant = next(p for p in response.json()["participants"] if p["email"] == participant.email)
    assert my_participant["rsvp_status"] == "pending"


def test_non_participant_gets_403(client, db_session, make_user, auth_headers):
    organizer = make_user()
    participant = make_user()
    outsider = make_user()
    meeting = _make_meeting_with_participant(db_session, organizer, participant)

    response = client.patch(
        f"/api/v1/meetings/{meeting.id}/rsvp",
        json={"response": "akan_hadir"},
        headers=auth_headers(outsider),
    )

    assert response.status_code == 403


def test_nonexistent_meeting_gets_404(client, make_user, auth_headers):
    participant = make_user()

    response = client.patch(
        f"/api/v1/meetings/{uuid.uuid4()}/rsvp",
        json={"response": "akan_hadir"},
        headers=auth_headers(participant),
    )

    assert response.status_code == 404


def test_invalid_response_value_is_rejected(client, db_session, make_user, auth_headers):
    organizer = make_user()
    participant = make_user()
    meeting = _make_meeting_with_participant(db_session, organizer, participant)

    response = client.patch(
        f"/api/v1/meetings/{meeting.id}/rsvp",
        json={"response": "maybe"},
        headers=auth_headers(participant),
    )

    assert response.status_code == 422


def test_rsvp_does_not_leak_other_participants_checkin_tokens(client, db_session, make_user, auth_headers):
    organizer = make_user()
    participant = make_user()
    other_participant = make_user()
    meeting = _make_meeting_with_participant(db_session, organizer, participant)

    other_row = MeetingParticipant(
        meeting_id=meeting.id, user_id=other_participant.id, email=other_participant.email,
        role=ParticipantRole.peserta,
    )
    db_session.add(other_row)
    db_session.commit()
    db_session.refresh(other_row)
    db_session.add(
        Invitation(
            participant_id=other_row.id,
            token="super-secret-checkin-token",
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
        )
    )
    db_session.commit()

    response = client.patch(
        f"/api/v1/meetings/{meeting.id}/rsvp",
        json={"response": "akan_hadir"},
        headers=auth_headers(participant),
    )

    assert response.status_code == 200
    other_entry = next(p for p in response.json()["participants"] if p["email"] == other_participant.email)
    assert other_entry["checkin_token"] is None
