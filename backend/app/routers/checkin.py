from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.schemas.checkin import (
    CheckinPageResponse,
    CheckinConfirmResponse,
    CheckinActionItem,
    AttendanceUpdateRequest,
    AttendanceUpdateResponse,
    ActionItemStatusUpdate,
)
from app.services import checkin as checkin_service
from app.services.checkin import _get_participant_from_token
from app.services.pdf import generate_notulen_pdf

router = APIRouter(tags=["checkin"])


@router.get("/check-in/{token}", response_model=CheckinPageResponse)
def get_checkin_page(token: str, db: Session = Depends(get_db)):
    return checkin_service.get_checkin_info(db, token)


@router.post("/check-in/{token}/confirm", response_model=CheckinConfirmResponse)
def confirm_checkin(token: str, db: Session = Depends(get_db)):
    return checkin_service.confirm_checkin(db, token)


@router.patch("/check-in/{token}/action-items/{action_item_id}", response_model=CheckinActionItem)
def update_action_item_via_token(
    token: str,
    action_item_id: uuid.UUID,
    data: ActionItemStatusUpdate,
    db: Session = Depends(get_db),
):
    return checkin_service.update_action_item_via_token(db, token, action_item_id, data.status)


@router.get("/check-in/{token}/notulen.pdf")
def download_notulen_pdf_via_token(token: str, db: Session = Depends(get_db)):
    _, _, meeting = _get_participant_from_token(db, token)

    if meeting.summary is None:
        raise HTTPException(status_code=404, detail="Notulen belum tersedia")

    organizer_name = meeting.organizer.name if meeting.organizer else "Organizer"
    pdf_bytes = generate_notulen_pdf(
        meeting=meeting,
        organizer_name=organizer_name,
        participants=meeting.participants,
        summary=meeting.summary,
        action_items=meeting.action_items or [],
    )
    safe_title = "".join(c if c.isalnum() or c in " _-" else "_" for c in meeting.title)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="notulen-{safe_title}.pdf"'},
    )


@router.patch(
    "/meetings/{meeting_id}/participants/{participant_id}/attendance",
    response_model=AttendanceUpdateResponse,
)
def update_attendance_manual(
    meeting_id: uuid.UUID,
    participant_id: uuid.UUID,
    data: AttendanceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return checkin_service.update_attendance_manual(
        db=db,
        meeting_id=meeting_id,
        participant_id=participant_id,
        status_value=data.status,
        organizer_id=current_user.id,
    )
