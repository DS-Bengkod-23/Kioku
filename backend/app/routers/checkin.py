from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
import uuid
import io

from app.database import get_db
from app.rate_limit import limiter
from app.services.auth import get_current_user
from app.models.user import User
from app.schemas.checkin import (
    CheckinPageResponse,
    CheckinConfirmResponse,
    AttendanceUpdateRequest,
    AttendanceUpdateResponse,
    CheckinActionItemUpdateRequest,
)
from app.services import checkin as checkin_service

router = APIRouter(tags=["checkin"])


@router.get("/check-in/{token}", response_model=CheckinPageResponse)
@limiter.limit("30/minute")
def get_checkin_page(request: Request, token: str, db: Session = Depends(get_db)):
    return checkin_service.get_checkin_info(db, token)


@router.post("/check-in/{token}/confirm", response_model=CheckinConfirmResponse)
@limiter.limit("30/minute")
def confirm_checkin(request: Request, token: str, db: Session = Depends(get_db)):
    return checkin_service.confirm_checkin(db, token)


@router.patch("/check-in/{token}/action-items/{action_item_id}")
@limiter.limit("30/minute")
def update_checkin_action_item(
    request: Request,
    token: str,
    action_item_id: uuid.UUID,
    data: CheckinActionItemUpdateRequest,
    db: Session = Depends(get_db),
):
    return checkin_service.update_checkin_action_item(db, token, action_item_id, data.status)


@router.get("/check-in/{token}/notulen.pdf")
@limiter.limit("30/minute")
def download_checkin_notulen_pdf(request: Request, token: str, db: Session = Depends(get_db)):
    pdf_bytes = checkin_service.get_checkin_notulen_pdf(db, token)
    return StreamingResponse(
        io.BytesIO(pdf_bytes),
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=notulen.pdf"},
    )


@router.patch("/meetings/{meeting_id}/attendance/lock")
def lock_attendance(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return checkin_service.lock_attendance(db, meeting_id, current_user.id)


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
