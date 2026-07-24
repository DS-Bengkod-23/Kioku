import uuid
import logging
from datetime import date, timedelta
from typing import Optional
from sqlalchemy.orm import Session, joinedload, selectinload
from fastapi import HTTPException
from sqlalchemy import or_
from app.config import settings
from app.models.meeting import Meeting, MeetingStatus
from app.models.participant import MeetingParticipant, ParticipantRole, RsvpStatus
from app.models.attendance import Attendance, AttendanceStatus, AttendanceMethod
from app.models.user import User
from app.models.summary import Summary
from app.models.action_item import ActionItem
from app.models.calendar_sync_event import CalendarSyncEvent
from app.schemas.meeting import MeetingCreate, MeetingUpdate, MeetingListResponse
from app.services.invitation import create_invitations
from app.services.email import send_invitation_email
from app.tasks.calendar_sync import sync_meeting_calendar_task, delete_meeting_calendar_events_task

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
        location_building=data.location_building,
        location_room=data.location_room,
        location_city=data.location_city,
        description=data.description,
        agenda_text=data.agenda_text,
        duration_minutes=data.duration_minutes,
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

    for email in dict.fromkeys(data.participant_emails):  # dedupe, pertahankan urutan
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

        # create_invitations()/send_invitation_email() tidak lagi commit sendiri
        # (lihat catatan di invitation.py) — commit di sini supaya invitation &
        # email log yang baru dibuat benar-benar persist.
        db.commit()

    if settings.GOOGLE_CALENDAR_SYNC_ENABLED:
        sync_meeting_calendar_task.delay(str(meeting.id))

    return meeting


def get_meetings(
    db: Session,
    user_id: uuid.UUID,
    page: int = 1,
    limit: int = 10,
    status: Optional[str] = None,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> MeetingListResponse:
    # selectinload (bukan joinedload) untuk Meeting.participants: joinedload pada
    # relasi collection yang digabung dengan LIMIT/OFFSET/count() menyebabkan fan-out
    # baris SQL per participant, sehingga total jadi salah hitung dan participants
    # bisa terpotong di batas halaman. selectinload mengambil koleksi lewat query
    # terpisah setelah paginasi, jadi aman dipakai bersama LIMIT/OFFSET.
    query = db.query(Meeting).join(MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id).options(
        selectinload(Meeting.participants).joinedload(MeetingParticipant.attendance),
        joinedload(Meeting.recording),
    ).filter(
        MeetingParticipant.user_id == user_id
    ).distinct()

    if status:
        query = query.filter(Meeting.status == status)

    if date_from:
        query = query.filter(Meeting.scheduled_at >= date_from)

    if date_to:
        query = query.filter(Meeting.scheduled_at < date_to + timedelta(days=1))

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
    meeting = (
        db.query(Meeting)
        .options(
            joinedload(Meeting.organizer),
            joinedload(Meeting.participants).joinedload(MeetingParticipant.user),
            joinedload(Meeting.participants).joinedload(MeetingParticipant.attendance),
            joinedload(Meeting.participants).joinedload(MeetingParticipant.invitation),
            joinedload(Meeting.action_items)
            .joinedload(ActionItem.assignee_participant)
            .joinedload(MeetingParticipant.user),
            joinedload(Meeting.recording),
            joinedload(Meeting.transcript),
            joinedload(Meeting.summary),
        )
        .filter(Meeting.id == meeting_id)
        .first()
    )
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

    update_data = data.model_dump(exclude_unset=True, exclude={"participant_emails"})
    for key, value in update_data.items():
        setattr(meeting, key, value)

    removed_calendar_events: list[dict] = []
    if data.participant_emails is not None:
        organizer_user = db.query(User).filter(User.id == user_id).first()
        organizer_email = organizer_user.email if organizer_user else None

        existing_peserta = {
            p.email: p
            for p in meeting.participants
            if p.role == ParticipantRole.peserta
        }
        new_emails = {e for e in data.participant_emails if e != organizer_email}
        removed_participants = [p for email, p in existing_peserta.items() if email not in new_emails]

        # Tangkap dulu google_event_id peserta yang mau dikeluarkan SEBELUM baris
        # MeetingParticipant-nya dihapus (CalendarSyncEvent ikut cascade delete
        # begitu itu terjadi) -- supaya event yang sudah nempel di Google Calendar
        # mereka bisa ikut dibersihkan, bukan dibiarkan nyangkut selamanya.
        if settings.GOOGLE_CALENDAR_SYNC_ENABLED and removed_participants:
            rows = (
                db.query(CalendarSyncEvent, MeetingParticipant.user_id)
                .join(MeetingParticipant, CalendarSyncEvent.meeting_participant_id == MeetingParticipant.id)
                .filter(MeetingParticipant.id.in_([p.id for p in removed_participants]))
                .all()
            )
            removed_calendar_events = [
                {"user_id": str(participant_user_id), "google_event_id": sync_event.google_event_id}
                for sync_event, participant_user_id in rows
            ]

        for participant in removed_participants:
            db.delete(participant)

        to_add = [e for e in new_emails if e not in existing_peserta]
        new_participants = []
        for email in to_add:
            existing_user = db.query(User).filter(User.email == email).first()
            p = MeetingParticipant(
                meeting_id=meeting.id,
                user_id=existing_user.id if existing_user else None,
                email=email,
                role=ParticipantRole.peserta,
            )
            db.add(p)
            new_participants.append((email, p))

        db.flush()

        if new_participants:
            invitations = create_invitations(
                db=db,
                meeting_id=meeting.id,
                participant_ids=[p.id for _, p in new_participants],
                expire_hours=settings.CHECKIN_TOKEN_EXPIRE_HOURS,
            )
            token_map = {inv.participant_id: inv.token for inv in invitations}

            for _, p in new_participants:
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

    db.commit()
    db.refresh(meeting)

    if removed_calendar_events:
        delete_meeting_calendar_events_task.delay(removed_calendar_events)

    if settings.GOOGLE_CALENDAR_SYNC_ENABLED:
        sync_meeting_calendar_task.delay(str(meeting.id))

    return meeting


def submit_rsvp(
    db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID, response: str, reason: str | None = None
) -> Meeting:
    participant = (
        db.query(MeetingParticipant)
        .filter(MeetingParticipant.meeting_id == meeting_id, MeetingParticipant.user_id == user_id)
        .first()
    )
    if participant is None:
        # Beda pesan tergantung sebabnya: meeting gak ada (404) vs meeting ada
        # tapi user ini bukan pesertanya (403) -- bukan dari checkin_token
        # seperti self check-in, RSVP dicari lewat current_user langsung.
        if not db.query(Meeting).filter(Meeting.id == meeting_id).first():
            raise HTTPException(status_code=404, detail="Meeting not found")
        raise HTTPException(status_code=403, detail="Not authorized to access this meeting")

    participant.rsvp_status = RsvpStatus(response)
    # Alasan cuma relevan buat "tidak_hadir" -- di-null-in kalau user konfirmasi
    # hadir, biar gak nyimpen keterangan yang gak relevan lagi.
    participant.rsvp_reason = reason if response == "tidak_hadir" else None
    db.commit()

    return get_meeting(db, meeting_id=meeting_id, user_id=user_id)


def complete_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID) -> Meeting:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting tidak ditemukan")
    if meeting.organizer_id != user_id:
        raise HTTPException(status_code=403, detail="Hanya organizer yang bisa menyelesaikan rapat")
    if meeting.status == MeetingStatus.completed:
        raise HTTPException(status_code=400, detail="Rapat sudah selesai")

    meeting.status = MeetingStatus.completed
    meeting.attendance_locked = True

    for p in meeting.participants:
        if p.role == ParticipantRole.peserta:
            if p.attendance:
                if p.attendance.status == AttendanceStatus.pending:
                    p.attendance.status = AttendanceStatus.tidak_hadir
            else:
                db.add(Attendance(
                    participant_id=p.id,
                    status=AttendanceStatus.tidak_hadir,
                    method=AttendanceMethod.manual,
                ))

    db.commit()
    db.refresh(meeting)
    return meeting


def delete_meeting(db: Session, meeting_id: uuid.UUID, user_id: uuid.UUID):
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=404, detail="Meeting not found")
        
    if meeting.organizer_id != user_id:
        raise HTTPException(status_code=403, detail="Only organizer can delete meeting")

    # Tangkap dulu event Calendar yang sudah ke-sync SEBELUM meeting (dan
    # MeetingParticipant-nya, lewat cascade) dihapus — setelah baris ini hilang,
    # google_event_id tidak bisa diambil lagi dari DB untuk proses cleanup di Google.
    events_to_delete = []
    if settings.GOOGLE_CALENDAR_SYNC_ENABLED:
        rows = (
            db.query(CalendarSyncEvent, MeetingParticipant.user_id)
            .join(MeetingParticipant, CalendarSyncEvent.meeting_participant_id == MeetingParticipant.id)
            .filter(MeetingParticipant.meeting_id == meeting_id)
            .all()
        )
        events_to_delete = [
            {"user_id": str(participant_user_id), "google_event_id": sync_event.google_event_id}
            for sync_event, participant_user_id in rows
        ]

    db.delete(meeting)
    db.commit()

    if events_to_delete:
        delete_meeting_calendar_events_task.delay(events_to_delete)


def search_meetings(
    db: Session,
    user_id: uuid.UUID,
    query: str,
    page: int = 1,
    limit: int = 10,
    date_from: Optional[date] = None,
    date_to: Optional[date] = None,
) -> MeetingListResponse:
    db_query = db.query(Meeting).join(
        MeetingParticipant, Meeting.id == MeetingParticipant.meeting_id
    ).outerjoin(
        Summary, Meeting.id == Summary.meeting_id
    ).outerjoin(
        ActionItem, Meeting.id == ActionItem.meeting_id
    ).options(
        selectinload(Meeting.participants).joinedload(MeetingParticipant.attendance),
        joinedload(Meeting.recording),
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

    if date_from:
        db_query = db_query.filter(Meeting.scheduled_at >= date_from)

    if date_to:
        db_query = db_query.filter(Meeting.scheduled_at < date_to + timedelta(days=1))

    total = db_query.count()
    offset = (page - 1) * limit
    meetings = db_query.order_by(Meeting.scheduled_at.desc()).offset(offset).limit(limit).all()

    return MeetingListResponse(
        items=meetings,
        total=total,
        page=page,
        limit=limit
    )

