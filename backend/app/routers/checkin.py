from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
import uuid

from app.database import get_db
from app.services.auth import get_current_user
from app.models.user import User
from app.schemas.checkin import (
    CheckinPageResponse,
    CheckinConfirmResponse,
    AttendanceUpdateRequest,
    AttendanceUpdateResponse
)
from app.services import checkin as checkin_service

router = APIRouter(tags=["checkin"])

@router.get("/check-in/{token}", response_model=CheckinPageResponse)
def get_checkin_page(token: str, db: Session = Depends(get_db)):
    return checkin_service.get_checkin_info(db, token)

@router.post("/check-in/{token}/confirm", response_model=CheckinConfirmResponse)
def confirm_checkin(token: str, db: Session = Depends(get_db)):
    return checkin_service.confirm_checkin(db, token)

@router.patch("/meetings/{meeting_id}/participants/{participant_id}/attendance", response_model=AttendanceUpdateResponse)
def update_attendance_manual(
    meeting_id: uuid.UUID,
    participant_id: uuid.UUID,
    data: AttendanceUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    return checkin_service.update_attendance_manual(
        db=db,
        meeting_id=meeting_id,
        participant_id=participant_id,
        status_value=data.status,
        organizer_id=current_user.id
    )
