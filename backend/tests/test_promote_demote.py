import pytest
from fastapi import HTTPException

from app.models.audit_log import AuditAction, AuditLog
from app.models.user import UserRole
from app.services import admin as admin_service


def test_superadmin_can_promote_user_to_admin(db_session, make_user):
    superadmin = make_user(role=UserRole.superadmin)
    target = make_user(role=UserRole.user)

    result = admin_service.update_user_role(db_session, superadmin, target.id, UserRole.admin)

    assert result.role == UserRole.admin


def test_promote_writes_audit_log_with_old_and_new_role(db_session, make_user):
    superadmin = make_user(role=UserRole.superadmin)
    target = make_user(role=UserRole.user)

    admin_service.update_user_role(db_session, superadmin, target.id, UserRole.admin)

    log = db_session.query(AuditLog).filter(AuditLog.target_id == target.id).one()
    assert log.action == AuditAction.promote_user
    assert log.reason == "role changed from user to admin"


def test_demote_writes_demote_action(db_session, make_user):
    superadmin = make_user(role=UserRole.superadmin)
    other_superadmin = make_user(role=UserRole.superadmin)
    target = make_user(role=UserRole.admin)

    admin_service.update_user_role(db_session, superadmin, target.id, UserRole.user)

    log = db_session.query(AuditLog).filter(AuditLog.target_id == target.id).one()
    assert log.action == AuditAction.demote_user
    assert other_superadmin.role == UserRole.superadmin  # unaffected, just needed as a second active superadmin


def test_cannot_demote_last_active_superadmin(db_session, make_user):
    only_superadmin = make_user(role=UserRole.superadmin)

    with pytest.raises(HTTPException) as exc_info:
        admin_service.update_user_role(db_session, only_superadmin, only_superadmin.id, UserRole.admin)
    assert exc_info.value.status_code == 403


def test_can_demote_superadmin_when_another_active_one_remains(db_session, make_user):
    acting_superadmin = make_user(role=UserRole.superadmin)
    target_superadmin = make_user(role=UserRole.superadmin)

    result = admin_service.update_user_role(db_session, acting_superadmin, target_superadmin.id, UserRole.admin)
    assert result.role == UserRole.admin


def test_non_superadmin_gets_403_on_role_endpoint(client, make_user, auth_headers):
    admin = make_user(role=UserRole.admin)
    target = make_user(role=UserRole.user)

    response = client.patch(
        f"/api/v1/admin/users/{target.id}/role",
        json={"role": "admin"},
        headers=auth_headers(admin),
    )
    assert response.status_code == 403
