from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.services.auth import get_current_admin_user
from app.services import admin as admin_service
from app.schemas.admin import UserAdminResponse, MeetingAdminResponse

router = APIRouter(tags=["admin"])


@router.get("/users", response_model=list[UserAdminResponse])
def list_users(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    return admin_service.list_users(db)


@router.get("/meetings", response_model=list[MeetingAdminResponse])
def list_meetings(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    return admin_service.list_meetings_metadata(db)
