import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.invitation import Invitation
from app.models.meeting import Meeting
from app.models.participant import MeetingParticipant
from app.models.attendance import Attendance, AttendanceStatus, AttendanceMethod
from app.models.recording import Recording
from app.models.summary import Summary
from app.models.action_item import ActionItem, ActionItemStatus
from app.schemas.checkin import (
    CheckinPageResponse,
    CheckinConfirmResponse,
    CheckinSummary,
    CheckinActionItem,
    AttendanceUpdateResponse,
)


def _is_attendance_locked(meeting: Meeting) -> bool:
    if meeting.attendance_locked_at:
        return datetime.now(timezone.utc) > meeting.attendance_locked_at
    grace = timedelta(minutes=30)
    scheduled_end = meeting.scheduled_at + timedelta(minutes=meeting.duration_minutes)
    return datetime.now(timezone.utc) > scheduled_end + grace


def _get_participant_from_token(db: Session, token: str) -> tuple[Invitation, MeetingParticipant, Meeting]:
    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token tidak valid atau tidak ditemukan")

    participant = db.query(MeetingParticipant).filter(
        MeetingParticipant.id == invitation.participant_id
    ).first()
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant tidak ditemukan")

    meeting = db.query(Meeting).filter(Meeting.id == participant.meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting tidak ditemukan")

    return invitation, participant, meeting


def get_checkin_info(db: Session, token: str) -> CheckinPageResponse:
    # Token tidak perlu cek expires_at — portal ini permanen untuk viewing
    invitation, participant, meeting = _get_participant_from_token(db, token)

    name = participant.user.name if participant.user else participant.email.split('@')[0]

    already_checked_in = False
    if invitation.used_at is not None:
        already_checked_in = True
    elif participant.attendance and participant.attendance.status == AttendanceStatus.hadir:
        already_checked_in = True

    attendance_locked = _is_attendance_locked(meeting)

    # Query recording status
    recording = db.query(Recording).filter(Recording.meeting_id == meeting.id).first()
    processing_status = recording.processing_status.value if recording else None

    # Query summary (hanya kalau ML sudah selesai)
    checkin_summary = None
    summary = db.query(Summary).filter(Summary.meeting_id == meeting.id).first()
    if summary:
        checkin_summary = CheckinSummary(
            tldr=summary.tldr,
            decisions=summary.decisions or [],
            topics=summary.topics or [],
        )

    # Query action items milik participant ini
    action_items = db.query(ActionItem).filter(
        ActionItem.meeting_id == meeting.id,
        ActionItem.assignee_participant_id == participant.id,
    ).all()

    checkin_action_items = [
        CheckinActionItem(
            id=ai.id,
            task=ai.task,
            due_date=ai.due_date,
            status=ai.status.value,
        )
        for ai in action_items
    ]

    return CheckinPageResponse(
        meeting_id=meeting.id,
        meeting_title=meeting.title,
        scheduled_at=meeting.scheduled_at,
        location=meeting.location,
        participant_name=name,
        already_checked_in=already_checked_in,
        attendance_locked=attendance_locked,
        processing_status=processing_status,
        summary=checkin_summary,
        action_items=checkin_action_items,
    )


def confirm_checkin(db: Session, token: str) -> CheckinConfirmResponse:
    invitation, participant, meeting = _get_participant_from_token(db, token)

    name = participant.user.name if participant.user else participant.email.split('@')[0]

    if _is_attendance_locked(meeting):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Absensi sudah ditutup untuk rapat ini",
        )

    if invitation.used_at is not None:
        return CheckinConfirmResponse(
            message="Kehadiran berhasil dikonfirmasi",
            participant_name=name,
            meeting_title=meeting.title,
        )

    invitation.used_at = datetime.now(timezone.utc)

    attendance = db.query(Attendance).filter(Attendance.participant_id == participant.id).first()
    if attendance:
        attendance.status = AttendanceStatus.hadir
        attendance.method = AttendanceMethod.link
        attendance.checked_in_at = datetime.now(timezone.utc)
    else:
        attendance = Attendance(
            participant_id=participant.id,
            status=AttendanceStatus.hadir,
            method=AttendanceMethod.link,
            checked_in_at=datetime.now(timezone.utc),
        )
        db.add(attendance)

    db.commit()

    return CheckinConfirmResponse(
        message="Kehadiran berhasil dikonfirmasi",
        participant_name=name,
        meeting_title=meeting.title,
    )


def update_action_item_via_token(
    db: Session, token: str, action_item_id: uuid.UUID, new_status: str
) -> CheckinActionItem:
    _, participant, _ = _get_participant_from_token(db, token)

    try:
        status_enum = ActionItemStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Status tidak valid. Gunakan 'open' atau 'done'")

    action_item = db.query(ActionItem).filter(
        ActionItem.id == action_item_id,
        ActionItem.assignee_participant_id == participant.id,
    ).first()
    if not action_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action item tidak ditemukan atau bukan milik Anda")

    action_item.status = status_enum
    db.commit()
    db.refresh(action_item)

    return CheckinActionItem(
        id=action_item.id,
        task=action_item.task,
        due_date=action_item.due_date,
        status=action_item.status.value,
    )


def update_attendance_manual(
    db: Session,
    meeting_id: uuid.UUID,
    participant_id: uuid.UUID,
    status_value: AttendanceStatus,
    organizer_id: uuid.UUID,
) -> AttendanceUpdateResponse:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting tidak ditemukan")

    if meeting.organizer_id != organizer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hanya organizer yang bisa update kehadiran")

    participant = db.query(MeetingParticipant).filter(
        MeetingParticipant.id == participant_id,
        MeetingParticipant.meeting_id == meeting_id,
    ).first()
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant tidak ada di meeting ini")

    attendance = db.query(Attendance).filter(Attendance.participant_id == participant.id).first()
    checked_in_at = datetime.now(timezone.utc) if status_value == AttendanceStatus.hadir else None

    if attendance:
        attendance.status = status_value
        attendance.method = AttendanceMethod.manual
        if checked_in_at:
            attendance.checked_in_at = checked_in_at
    else:
        attendance = Attendance(
            participant_id=participant.id,
            status=status_value,
            method=AttendanceMethod.manual,
            checked_in_at=checked_in_at,
        )
        db.add(attendance)

    db.commit()

    name = participant.user.name if participant.user else participant.email.split('@')[0]

    return AttendanceUpdateResponse(
        participant_id=participant.id,
        name=name,
        status=status_value,
        method=AttendanceMethod.manual,
    )
