import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.models.user import User, UserRole
from app.models.meeting import Meeting
from app.models.participant import MeetingParticipant
from app.models.action_item import ActionItemStatus
from app.models.audit_log import AuditLog, AuditAction
from app.schemas.admin import (
    UserAdminResponse,
    MeetingAdminResponse,
    ParticipantAdminResponse,
    ActionItemsSummary,
)


def list_users(db: Session) -> list[UserAdminResponse]:
    users = db.query(User).order_by(User.created_at).all()
    return [UserAdminResponse.model_validate(u) for u in users]


def _get_user_or_404(db: Session, user_id: uuid.UUID) -> User:
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User tidak ditemukan")
    return user


def _assert_actor_can_target(actor: User, target: User) -> None:
    # Admin can only act on regular users — never on another admin or a
    # superadmin, in either direction (suspend or unsuspend).
    if actor.role == UserRole.admin and target.role in (UserRole.admin, UserRole.superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin tidak dapat menargetkan akun admin/superadmin lain",
        )


def _active_superadmin_count(db: Session) -> int:
    return (
        db.query(User)
        .filter(User.role == UserRole.superadmin, User.suspended_at.is_(None))
        .count()
    )


def suspend_user(db: Session, actor: User, target_user_id: uuid.UUID) -> User:
    target = _get_user_or_404(db, target_user_id)
    _assert_actor_can_target(actor, target)

    if target.suspended_at is not None:
        return target  # already suspended — idempotent no-op

    if target.role == UserRole.superadmin and _active_superadmin_count(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tidak boleh menyisakan sistem tanpa superadmin aktif",
        )

    target.suspended_at = datetime.now(timezone.utc)
    db.add(
        AuditLog(
            actor_id=actor.id,
            action=AuditAction.suspend_user,
            target_type="user",
            target_id=target.id,
        )
    )
    db.commit()
    db.refresh(target)
    return target


def unsuspend_user(db: Session, actor: User, target_user_id: uuid.UUID) -> User:
    target = _get_user_or_404(db, target_user_id)
    _assert_actor_can_target(actor, target)

    if target.suspended_at is None:
        return target  # already active — idempotent no-op

    target.suspended_at = None
    db.add(
        AuditLog(
            actor_id=actor.id,
            action=AuditAction.unsuspend_user,
            target_type="user",
            target_id=target.id,
        )
    )
    db.commit()
    db.refresh(target)
    return target


def list_meetings_metadata(db: Session) -> list[MeetingAdminResponse]:
    # Metadata-only by construction: transcript/summary/notulen are never
    # touched here — that content only flows through the justified,
    # audit-logged meeting-content-access endpoint.
    meetings = (
        db.query(Meeting)
        .options(
            joinedload(Meeting.organizer),
            joinedload(Meeting.participants).joinedload(MeetingParticipant.attendance),
            joinedload(Meeting.action_items),
        )
        .order_by(Meeting.scheduled_at.desc())
        .all()
    )

    result: list[MeetingAdminResponse] = []
    for meeting in meetings:
        participants = [
            ParticipantAdminResponse(
                name=p.user.name if p.user else p.email,
                email=p.email,
                role=p.role,
                attendance_status=p.attendance.status if p.attendance else None,
            )
            for p in meeting.participants
        ]
        open_count = sum(1 for item in meeting.action_items if item.status == ActionItemStatus.open)
        done_count = sum(1 for item in meeting.action_items if item.status == ActionItemStatus.done)
        result.append(
            MeetingAdminResponse(
                id=meeting.id,
                title=meeting.title,
                scheduled_at=meeting.scheduled_at,
                status=meeting.status,
                organizer_name=meeting.organizer.name,
                organizer_email=meeting.organizer.email,
                participants=participants,
                action_items=ActionItemsSummary(open=open_count, done=done_count),
            )
        )
    return result
