from sqlalchemy.orm import Session, joinedload
from app.models.user import User
from app.models.meeting import Meeting
from app.models.participant import MeetingParticipant
from app.models.action_item import ActionItemStatus
from app.schemas.admin import (
    UserAdminResponse,
    MeetingAdminResponse,
    ParticipantAdminResponse,
    ActionItemsSummary,
)


def list_users(db: Session) -> list[UserAdminResponse]:
    users = db.query(User).order_by(User.created_at).all()
    return [UserAdminResponse.model_validate(u) for u in users]


def list_meetings_metadata(db: Session) -> list[MeetingAdminResponse]:
    # Metadata-only by construction: transcript/summary/notulen are never
    # touched here — that content only flows through the justified,
    # audit-logged meeting-content-access endpoint.
    meetings = (
        db.query(Meeting)
        .options(
            joinedload(Meeting.organizer),
            joinedload(Meeting.participants).joinedload(MeetingParticipant.attendance),
            joinedload(Meeting.action_items),
        )
        .order_by(Meeting.scheduled_at.desc())
        .all()
    )

    result: list[MeetingAdminResponse] = []
    for meeting in meetings:
        participants = [
            ParticipantAdminResponse(
                name=p.user.name if p.user else p.email,
                email=p.email,
                role=p.role,
                attendance_status=p.attendance.status if p.attendance else None,
            )
            for p in meeting.participants
        ]
        open_count = sum(1 for item in meeting.action_items if item.status == ActionItemStatus.open)
        done_count = sum(1 for item in meeting.action_items if item.status == ActionItemStatus.done)
        result.append(
            MeetingAdminResponse(
                id=meeting.id,
                title=meeting.title,
                scheduled_at=meeting.scheduled_at,
                status=meeting.status,
                organizer_name=meeting.organizer.name,
                organizer_email=meeting.organizer.email,
                participants=participants,
                action_items=ActionItemsSummary(open=open_count, done=done_count),
            )
        )
    return result
