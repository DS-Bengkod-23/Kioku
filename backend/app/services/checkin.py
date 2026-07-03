import uuid
from datetime import datetime, timezone, timedelta
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.models.invitation import Invitation
from app.models.meeting import Meeting
from app.models.participant import MeetingParticipant, ParticipantRole
from app.models.attendance import Attendance, AttendanceStatus, AttendanceMethod
from app.models.action_item import ActionItem, ActionItemStatus
from app.models.summary import Summary as SummaryModel
from app.services.pdf import generate_notulen_pdf
from app.schemas.checkin import (
    CheckinPageResponse,
    CheckinConfirmResponse,
    AttendanceUpdateResponse,
)


def _resolve_token(db: Session, token: str):
    # Token portal tidak pernah expire by design (lihat plan/plan-checkin-portal.md) —
    # peserta harus bisa akses notulen & action items kapan pun. Aksi yang sensitif
    # terhadap waktu (check-in baru) tetap dijaga terpisah lewat attendance_locked
    # dan pengecekan meeting_end di confirm_checkin, bukan lewat expiry token ini.
    invitation = db.query(Invitation).filter(Invitation.token == token).first()
    if not invitation:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Token tidak valid atau tidak ditemukan")
    participant = db.query(MeetingParticipant).filter(MeetingParticipant.id == invitation.participant_id).first()
    if not participant:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Participant tidak ditemukan")
    meeting = db.query(Meeting).filter(Meeting.id == participant.meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting tidak ditemukan")
    return invitation, participant, meeting


def get_checkin_info(db: Session, token: str) -> CheckinPageResponse:
    invitation, participant, meeting = _resolve_token(db, token)

    name = participant.user.name if participant.user else participant.email.split('@')[0]

    already_checked_in = False
    if invitation.used_at is not None:
        already_checked_in = True
    elif participant.attendance and participant.attendance.status == AttendanceStatus.hadir:
        already_checked_in = True

    processing_status = None
    if meeting.recording:
        ps = meeting.recording.processing_status
        processing_status = ps.value if hasattr(ps, 'value') else ps

    summary = None
    summary_obj = db.query(SummaryModel).filter(SummaryModel.meeting_id == meeting.id).first()
    if summary_obj:
        summary = {
            "tldr": summary_obj.tldr,
            "decisions": summary_obj.decisions or [],
            "topics": summary_obj.topics or [],
        }

    action_items = [
        {
            "id": str(ai.id),
            "task": ai.task,
            "due_date": ai.due_date.isoformat() if ai.due_date else None,
            "status": ai.status.value if hasattr(ai.status, 'value') else ai.status,
        }
        for ai in meeting.action_items
        if ai.assignee_participant_id == participant.id
    ]

    # Samakan dengan pengecekan di confirm_checkin() supaya halaman check-in
    # menampilkan status "ditutup" yang benar SEBELUM peserta klik tombol,
    # bukan cuma setelah submit ditolak backend.
    meeting_end = meeting.scheduled_at + timedelta(minutes=meeting.duration_minutes)
    time_expired = datetime.now(timezone.utc) > meeting_end

    return CheckinPageResponse(
        meeting_id=meeting.id,
        meeting_title=meeting.title,
        scheduled_at=meeting.scheduled_at,
        location=meeting.location,
        participant_name=name,
        already_checked_in=already_checked_in,
        attendance_locked=meeting.attendance_locked or time_expired,
        processing_status=processing_status,
        summary=summary,
        action_items=action_items,
    )


def confirm_checkin(db: Session, token: str) -> CheckinConfirmResponse:
    invitation, participant, meeting = _resolve_token(db, token)

    name = participant.user.name if participant.user else participant.email.split('@')[0]

    if meeting.attendance_locked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Absensi sudah ditutup untuk rapat ini",
        )

    meeting_end = meeting.scheduled_at + timedelta(minutes=meeting.duration_minutes)
    if datetime.now(timezone.utc) > meeting_end:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Waktu absensi sudah berakhir",
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


def lock_attendance(db: Session, meeting_id: uuid.UUID, organizer_id: uuid.UUID) -> dict:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if not meeting:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting tidak ditemukan")
    if meeting.organizer_id != organizer_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Hanya organizer yang bisa mengunci presensi")

    meeting.attendance_locked = True

    peserta = [p for p in meeting.participants if p.role == ParticipantRole.peserta]
    for p in peserta:
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
    return {"attendance_locked": True}


def update_checkin_action_item(
    db: Session, token: str, action_item_id: uuid.UUID, new_status: ActionItemStatus
) -> dict:
    _, participant, meeting = _resolve_token(db, token)

    action_item = db.query(ActionItem).filter(
        ActionItem.id == action_item_id,
        ActionItem.meeting_id == meeting.id,
        ActionItem.assignee_participant_id == participant.id,
    ).first()
    if not action_item:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Action item tidak ditemukan atau bukan milik Anda")

    action_item.status = new_status
    db.commit()
    return {
        "id": str(action_item.id),
        "task": action_item.task,
        "due_date": action_item.due_date.isoformat() if action_item.due_date else None,
        "status": action_item.status.value,
    }


def get_checkin_notulen_pdf(db: Session, token: str) -> bytes:
    _, participant, meeting = _resolve_token(db, token)

    if not meeting.summary:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Notulen belum tersedia")

    organizer_name = meeting.organizer.name if meeting.organizer else "Organizer"
    return generate_notulen_pdf(
        meeting=meeting,
        organizer_name=organizer_name,
        participants=meeting.participants,
        summary=meeting.summary,
        action_items=meeting.action_items or [],
        viewer_participant_id=participant.id,
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
