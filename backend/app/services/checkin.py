import uuid
from datetime import datetime, timezone
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.invitation import Invitation
from app.models.meeting import Meeting
from app.models.participant import MeetingParticipant
from app.models.attendance import Attendance, AttendanceStatus, AttendanceMethod
from app.schemas.checkin import (
    CheckinPageResponse,
    CheckinConfirmResponse,
    AttendanceUpdateResponse
)

def get_checkin_info(db: Session, token: str) -> CheckinPageResponse:
    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token tidak valid atau tidak ditemukan")

    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token sudah expired")

    participant = db.query(MeetingParticipant).filter(MeetingParticipant.id == invitation.participant_id).first()
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant tidak ditemukan")

    meeting = db.query(Meeting).filter(Meeting.id == participant.meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting tidak ditemukan")

    name = participant.user.name if participant.user else participant.email.split('@')[0]
    
    already_checked_in = False
    if invitation.used_at is not None:
        already_checked_in = True
    elif participant.attendance and participant.attendance.status == AttendanceStatus.hadir:
        already_checked_in = True

    return CheckinPageResponse(
        meeting_title=meeting.title,
        scheduled_at=meeting.scheduled_at,
        location=meeting.location,
        participant_name=name,
        already_checked_in=already_checked_in
    )

def confirm_checkin(db: Session, token: str) -> CheckinConfirmResponse:
    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token tidak valid atau tidak ditemukan")

    if invitation.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token sudah expired")

    participant = db.query(MeetingParticipant).filter(MeetingParticipant.id == invitation.participant_id).first()
    meeting = db.query(Meeting).filter(Meeting.id == participant.meeting_id).first()
    
    name = participant.user.name if participant.user else participant.email.split('@')[0]

    if invitation.used_at is not None:
        return CheckinConfirmResponse(
            message="Kehadiran berhasil dikonfirmasi",
            participant_name=name,
            meeting_title=meeting.title
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
            checked_in_at=datetime.now(timezone.utc)
        )
        db.add(attendance)
        
    db.commit()
    
    return CheckinConfirmResponse(
        message="Kehadiran berhasil dikonfirmasi",
        participant_name=name,
        meeting_title=meeting.title
    )

def update_attendance_manual(
    db: Session, 
    meeting_id: uuid.UUID, 
    participant_id: uuid.UUID, 
    status_value: AttendanceStatus, 
    organizer_id: uuid.UUID
) -> AttendanceUpdateResponse:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting tidak ditemukan")
        
    if meeting.organizer_id != organizer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hanya organizer yang bisa update kehadiran")
        
    participant = db.query(MeetingParticipant).filter(
        MeetingParticipant.id == participant_id,
        MeetingParticipant.meeting_id == meeting_id
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
            checked_in_at=checked_in_at
        )
        db.add(attendance)
        
    db.commit()
    
    name = participant.user.name if participant.user else participant.email.split('@')[0]
    
    return AttendanceUpdateResponse(
        participant_id=participant.id,
        name=name,
        status=status_value,
        method=AttendanceMethod.manual
    )
