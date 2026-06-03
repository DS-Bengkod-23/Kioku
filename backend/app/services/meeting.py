import uuid
import logging
from typing import Optional
from sqlalchemy.orm import Session
from fastapi import HTTPException
from sqlalchemy import or_
from app.config import settings
from app.models.meeting import Meeting, MeetingStatus
from app.models.participant import MeetingParticipant, ParticipantRole
from app.models.user import User
from app.models.summary import Summary
from app.models.action_item import ActionItem
from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingListResponse
from app.services.invitation import create_invitations
from app.services.email import send_invitation_email

logger = logging.getLogger(__name__)


def create_meeting(db: Session, organizer_id: uuid.UUID, data: MeetingCreate) -> Meeting:
    organizer_user = db.query(User).filter(User.id == organizer_id).first()
    if not organizer_user:
        raise HTTPException(status_code=404, detail="Organizer not found")

    meeting = Meeting(
        organizer_id=organizer_id,
        title=data.title,
        scheduled_at=data.scheduled_at,
        location=data.location,
        description=data.description,
        agenda_text=data.agenda_text
    )
    db.add(meeting)
    db.flush()

    org_participant = MeetingParticipant(
        meeting_id=meeting.id,
        user_id=organizer_id,
        email=organizer_user.email,
        role=ParticipantRole.organizer
    )
    db.add(org_participant)

    for email in data.participant_emails:
        if email == organizer_user.email:
            continue
        existing_user = db.query(User).filter(User.email == email).first()
        p = MeetingParticipant(
            meeting_id=meeting.id,
            user_id=existing_user.id if existing_user else None,
            email=email,
            role=ParticipantRole.peserta
        )
        db.add(p)
    
    db.commit()
    db.refresh(meeting)

    peserta = [p for p in meeting.participants if p.role == ParticipantRole.peserta]
    if peserta:
        invitations = create_invitations(
            db=db,
            meeting_id=meeting.id,
            participant_ids=[p.id for p in peserta],
            expire_hours=settings.CHECKIN_TOKEN_EXPIRE_HOURS,
        )
        token_map = {inv.participant_id: inv.token for inv in invitations}

        for p in peserta:
            try:
                send_invitation_email(
                    recipient_email=p.email,
                    recipient_name=p.user.name if p.user else p.email,
                    meeting_title=meeting.title,
                    scheduled_at=meeting.scheduled_at,
                    location=meeting.location or "",
                    checkin_token=token_map[p.id],
                    meeting_id=meeting.id,
                    db=db,
                )
            except Exception:
                logger.exception("Failed to send invitation email to %s", p.email)

    return meeting


def get_meetings(db: Session, user_id: uuid.UUID, page: int = 1, limit: int = 10, status: Optional[str] = None) -> MeetingListResponse:
    query = db.query(Meeting).join(MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id).filter(
        MeetingParticipant.user_id == user_id
    ).distinct()

    if status:
        query = query.filter(Meeting.status == status)

    total = query.count()
    
    offset = (page - 1) * limit
    meetings = query.order_by(Meeting.scheduled_at.desc()).offset(offset).limit(limit).all()

    return MeetingListResponse(
        items=meetings,
        total=total,
        page=page,
        limit=limit
    )


def get_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Meeting:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    is_participant = any(p.user_id == user_id for p in meeting.participants)
    
    if not is_participant:
        raise HTTPException(status_code=403, detail="Not authorized to access this meeting")
        
    return meeting


def update_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, data: MeetingUpdate) -> Meeting:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if meeting.organizer_id != user_id:
        raise HTTPException(status_code=403, detail="Only organizer can update meeting")
        
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(meeting, key, value)
        
    db.commit()
    db.refresh(meeting)
    return meeting


def delete_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if meeting.organizer_id != user_id:
        raise HTTPException(status_code=403, detail="Only organizer can delete meeting")
        
    db.delete(meeting)
    db.commit()


def search_meetings(db: Session, user_id: uuid.UUID, query: str, page: int = 1, limit: int = 10) -> MeetingListResponse:
    db_query = db.query(Meeting).join(
        MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id
    ).outerjoin(
        Summary, Meeting.id == Summary.meeting_id
    ).outerjoin(
        ActionItem, Meeting.id == ActionItem.meeting_id
    ).filter(
        MeetingParticipant.user_id == user_id
    )

    search_pattern = f"%{query}%"
    db_query = db_query.filter(
        or_(
            Meeting.title.ilike(search_pattern),
            Summary.tldr.ilike(search_pattern),
            ActionItem.task.ilike(search_pattern)
        )
    ).distinct()

    total = db_query.count()
    offset = (page - 1) * limit
    meetings = db_query.order_by(Meeting.scheduled_at.desc()).offset(offset).limit(limit).all()

    return MeetingListResponse(
        items=meetings,
        total=total,
        page=page,
        limit=limit
    )

