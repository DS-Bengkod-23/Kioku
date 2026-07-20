import uuid
from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.orm import Session
from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_admin_user, get_current_superadmin_user
from app.services import admin as admin_service
from app.schemas.admin import (
    UserAdminResponse,
    MeetingAdminResponse,
    UserRoleUpdateRequest,
    MeetingContentAccessRequest,
    MeetingContentAccessResponse,
    AuditLogResponse,
)

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


@router.patch("/users/{user_id}/role", response_model=UserAdminResponse)
def update_user_role(
    user_id: uuid.UUID,
    body: UserRoleUpdateRequest,
    db: Session = Depends(get_db),
    superadmin: User = Depends(get_current_superadmin_user),
):
    return admin_service.update_user_role(db, superadmin, user_id, body.role)


@router.post("/users/{user_id}/reset-password", status_code=status.HTTP_202_ACCEPTED)
def reset_user_password(
    user_id: uuid.UUID,
    db: Session = Depends(get_db),
    superadmin: User = Depends(get_current_superadmin_user),
):
    admin_service.trigger_password_reset(db, superadmin, user_id)
    return {"detail": "Email reset password telah dikirim"}


@router.post("/meetings/{meeting_id}/access-requests", response_model=MeetingContentAccessResponse)
def request_meeting_access(
    meeting_id: uuid.UUID,
    body: MeetingContentAccessRequest,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    return admin_service.request_meeting_content_access(db, admin, meeting_id, body.reason)


@router.delete("/meetings/{meeting_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_meeting(
    meeting_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    admin_service.delete_meeting(db, admin, meeting_id)


@router.delete("/recordings/{recording_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_recording(
    recording_id: uuid.UUID,
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    admin_service.delete_recording(db, admin, recording_id)


@router.get("/audit-logs", response_model=list[AuditLogResponse])
def list_audit_logs(
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    admin: User = Depends(get_current_admin_user),
):
    return admin_service.list_audit_logs(db, admin, limit=limit, offset=offset)


@router.get("/meetings", response_model=list[MeetingAdminResponse])
def list_meetings(
    db: Session = Depends(get_db),
    _admin=Depends(get_current_admin_user),
):
    return admin_service.list_meetings_metadata(db)
