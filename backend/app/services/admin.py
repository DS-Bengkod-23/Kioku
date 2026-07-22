import uuid
from datetime import datetime, timezone
from fastapi import HTTPException, status
from sqlalchemy.orm import Session, joinedload
from app.models.user import User, UserRole
from app.models.meeting import Meeting
from app.models.recording import Recording
from app.models.participant import MeetingParticipant
from app.models.action_item import ActionItemStatus
from app.models.audit_log import AuditLog, AuditAction
from app.services.auth import create_password_reset_token
from app.services.email import send_password_reset_email
from app.schemas.admin import (
    UserAdminResponse,
    MeetingAdminResponse,
    ParticipantAdminResponse,
    ActionItemsSummary,
    MeetingContentAccessResponse,
    AuditLogResponse,
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


_ROLE_RANK = {UserRole.user: 0, UserRole.admin: 1, UserRole.superadmin: 2}


def update_user_role(db: Session, actor: User, target_user_id: uuid.UUID, new_role: UserRole) -> User:
    target = _get_user_or_404(db, target_user_id)
    old_role = target.role

    if old_role == new_role:
        return target  # no-op

    if old_role == UserRole.superadmin and _active_superadmin_count(db) <= 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Tidak boleh menyisakan sistem tanpa superadmin aktif",
        )

    target.role = new_role
    action = (
        AuditAction.promote_user if _ROLE_RANK[new_role] > _ROLE_RANK[old_role] else AuditAction.demote_user
    )
    db.add(
        AuditLog(
            actor_id=actor.id,
            action=action,
            target_type="user",
            target_id=target.id,
            reason=f"role changed from {old_role.value} to {new_role.value}",
        )
    )
    db.commit()
    db.refresh(target)
    return target


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


def request_meeting_content_access(
    db: Session, actor: User, meeting_id: uuid.UUID, reason: str
) -> MeetingContentAccessResponse:
    meeting = (
        db.query(Meeting)
        .options(joinedload(Meeting.transcript), joinedload(Meeting.summary))
        .filter(Meeting.id == meeting_id)
        .first()
    )
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting tidak ditemukan")

    # No persisted "grant" — every call is its own justified, logged access.
    # No notification to organizer/participants, by design (never add one).
    db.add(
        AuditLog(
            actor_id=actor.id,
            action=AuditAction.request_meeting_access,
            target_type="meeting",
            target_id=meeting.id,
            reason=reason,
        )
    )
    db.commit()

    return MeetingContentAccessResponse(
        meeting_id=meeting.id,
        transcript_segments=meeting.transcript.segments if meeting.transcript else None,
        summary_tldr=meeting.summary.tldr if meeting.summary else None,
        summary_decisions=meeting.summary.decisions if meeting.summary else None,
        summary_topics=meeting.summary.topics if meeting.summary else None,
    )


def list_audit_logs(db: Session, actor: User, limit: int = 50, offset: int = 0) -> list[AuditLogResponse]:
    query = (
        db.query(AuditLog)
        .options(joinedload(AuditLog.actor))
        .order_by(AuditLog.created_at.desc())
    )
    if actor.role == UserRole.admin:
        # Admin sees only their own actions; superadmin sees everything.
        query = query.filter(AuditLog.actor_id == actor.id)
    logs = query.offset(offset).limit(limit).all()
    return [
        AuditLogResponse(
            id=log.id,
            actor_id=log.actor_id,
            # actor can be None if the actor's account was later removed
            # (no hard-delete exists yet, but actor_id is SET NULL-capable).
            actor_name=log.actor.name if log.actor else None,
            actor_email=log.actor.email if log.actor else None,
            action=log.action,
            target_type=log.target_type,
            target_id=log.target_id,
            reason=log.reason,
            created_at=log.created_at,
        )
        for log in logs
    ]


def delete_meeting(db: Session, actor: User, meeting_id: uuid.UUID) -> None:
    meeting = db.query(Meeting).filter(Meeting.id == meeting_id).first()
    if meeting is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Meeting tidak ditemukan")
    if meeting.deleted_at is not None:
        return  # idempotent no-op

    meeting.deleted_at = datetime.now(timezone.utc)
    meeting.deleted_by_admin_id = actor.id
    db.add(
        AuditLog(
            actor_id=actor.id,
            action=AuditAction.delete_meeting,
            target_type="meeting",
            target_id=meeting.id,
        )
    )
    db.commit()


def delete_recording(db: Session, actor: User, recording_id: uuid.UUID) -> None:
    recording = db.query(Recording).filter(Recording.id == recording_id).first()
    if recording is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Recording tidak ditemukan")
    if recording.deleted_at is not None:
        return  # idempotent no-op

    recording.deleted_at = datetime.now(timezone.utc)
    recording.deleted_by_admin_id = actor.id
    db.add(
        AuditLog(
            actor_id=actor.id,
            action=AuditAction.delete_recording,
            target_type="recording",
            target_id=recording.id,
        )
    )
    db.commit()


def trigger_password_reset(db: Session, actor: User, target_user_id: uuid.UUID) -> None:
    target = _get_user_or_404(db, target_user_id)

    if target.password_hash is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User ini tidak punya password lokal (akun Google SSO) — tidak ada yang bisa direset",
        )

    # Superadmin never sees or sets the new password — the token only lets
    # the account owner themselves choose it via the confirm endpoint.
    token = create_password_reset_token(target.id)
    send_password_reset_email(target.email, target.name, token)

    db.add(
        AuditLog(
            actor_id=actor.id,
            action=AuditAction.reset_password,
            target_type="user",
            target_id=target.id,
        )
    )
    db.commit()


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
