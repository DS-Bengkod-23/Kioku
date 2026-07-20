import uuid
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
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


@router.patch("/users/{user_id}/suspend", response_model=UserAdminResponse)
def suspend_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    return admin_service.suspend_user(db, admin, user_id)


@router.patch("/users/{user_id}/unsuspend", response_model=UserAdminResponse)
def unsuspend_user(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    return admin_service.unsuspend_user(db, admin, user_id)


@router.get("/meetings", response_model=list[MeetingAdminResponse])
def list_meetings(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    return admin_service.list_meetings_metadata(db)
