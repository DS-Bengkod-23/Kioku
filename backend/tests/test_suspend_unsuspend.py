from datetime import datetime, timezone

import pytest
from fastapi import HTTPException

from app.models.audit_log import AuditAction, AuditLog
from app.models.user import UserRole
from app.services import admin as admin_service


def test_admin_can_suspend_regular_user(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    target = make_user(role=UserRole.user)

    result = admin_service.suspend_user(db_session, admin, target.id)

    assert result.suspended_at is not None


def test_admin_cannot_suspend_admin(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    other_admin = make_user(role=UserRole.admin)

    with pytest.raises(HTTPException) as exc_info:
        admin_service.suspend_user(db_session, admin, other_admin.id)
    assert exc_info.value.status_code == 403


def test_admin_cannot_suspend_superadmin(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    superadmin = make_user(role=UserRole.superadmin)

    with pytest.raises(HTTPException) as exc_info:
        admin_service.suspend_user(db_session, admin, superadmin.id)
    assert exc_info.value.status_code == 403


def test_superadmin_can_suspend_admin(db_session, make_user):
    superadmin = make_user(role=UserRole.superadmin)
    admin = make_user(role=UserRole.admin)

    result = admin_service.suspend_user(db_session, superadmin, admin.id)
    assert result.suspended_at is not None


def test_cannot_suspend_last_active_superadmin(db_session, make_user):
    only_superadmin = make_user(role=UserRole.superadmin)

    with pytest.raises(HTTPException) as exc_info:
        admin_service.suspend_user(db_session, only_superadmin, only_superadmin.id)
    assert exc_info.value.status_code == 403


def test_can_suspend_superadmin_when_another_active_one_remains(db_session, make_user):
    acting_superadmin = make_user(role=UserRole.superadmin)
    target_superadmin = make_user(role=UserRole.superadmin)

    result = admin_service.suspend_user(db_session, acting_superadmin, target_superadmin.id)
    assert result.suspended_at is not None


def test_suspend_then_unsuspend_reactivates_user(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    target = make_user(role=UserRole.user)

    admin_service.suspend_user(db_session, admin, target.id)
    result = admin_service.unsuspend_user(db_session, admin, target.id)

    assert result.suspended_at is None


def test_admin_cannot_unsuspend_admin(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    other_admin = make_user(role=UserRole.admin)

    with pytest.raises(HTTPException) as exc_info:
        admin_service.unsuspend_user(db_session, admin, other_admin.id)
    assert exc_info.value.status_code == 403


def test_suspend_writes_audit_log(db_session, make_user):
    admin = make_user(role=UserRole.admin)
    target = make_user(role=UserRole.user)

    admin_service.suspend_user(db_session, admin, target.id)

    log = db_session.query(AuditLog).filter(AuditLog.target_id == target.id).one()
    assert log.actor_id == admin.id
    assert log.action == AuditAction.suspend_user


def test_suspended_user_rejected_on_next_request_with_existing_token(client, make_user, auth_headers, db_session):
    user = make_user(role=UserRole.user)
    headers = auth_headers(user)

    assert client.get("/api/v1/auth/me", headers=headers).status_code == 200

    user.suspended_at = datetime.now(timezone.utc)
    db_session.add(user)
    db_session.commit()

    # Same, still-unexpired token — must be rejected on the very next call.
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 401
