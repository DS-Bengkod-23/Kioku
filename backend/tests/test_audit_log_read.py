import uuid

from app.models.audit_log import AuditAction, AuditLog
from app.models.user import UserRole
from app.services import admin as admin_service


def test_admin_sees_only_own_actions(db_session, make_user):
    admin_a = make_user(role=UserRole.admin)
    admin_b = make_user(role=UserRole.admin)
    target = make_user(role=UserRole.user)

    admin_service.suspend_user(db_session, admin_a, target.id)
    admin_service.unsuspend_user(db_session, admin_a, target.id)

    other_target = make_user(role=UserRole.user)
    admin_service.suspend_user(db_session, admin_b, other_target.id)

    results = admin_service.list_audit_logs(db_session, admin_a)

    assert len(results) == 2
    assert all(log.actor_id == admin_a.id for log in results)


def test_superadmin_sees_all_actions(db_session, make_user):
    admin_a = make_user(role=UserRole.admin)
    superadmin = make_user(role=UserRole.superadmin)
    target = make_user(role=UserRole.user)

    admin_service.suspend_user(db_session, admin_a, target.id)

    results = admin_service.list_audit_logs(db_session, superadmin)

    assert len(results) == 1
    assert results[0].actor_id == admin_a.id


def test_pagination_limit_and_offset(db_session, make_user):
    superadmin = make_user(role=UserRole.superadmin)
    for _ in range(5):
        db_session.add(
            AuditLog(
                actor_id=superadmin.id,
                action=AuditAction.suspend_user,
                target_type="user",
                target_id=uuid.uuid4(),
            )
        )
    db_session.commit()

    page_one = admin_service.list_audit_logs(db_session, superadmin, limit=2, offset=0)
    page_two = admin_service.list_audit_logs(db_session, superadmin, limit=2, offset=2)

    assert len(page_one) == 2
    assert len(page_two) == 2
    assert {log.id for log in page_one}.isdisjoint({log.id for log in page_two})


def test_regular_user_gets_403_on_audit_log_read(client, make_user, auth_headers):
    user = make_user(role=UserRole.user)
    response = client.get("/api/v1/admin/audit-logs", headers=auth_headers(user))
    assert response.status_code == 403


def test_no_write_route_exists_on_audit_logs(client, make_user, auth_headers):
    admin = make_user(role=UserRole.admin)

    patch_response = client.patch(
        "/api/v1/admin/audit-logs", json={}, headers=auth_headers(admin)
    )
    assert patch_response.status_code == 405

    delete_response = client.delete(
        f"/api/v1/admin/audit-logs/{uuid.uuid4()}", headers=auth_headers(admin)
    )
    assert delete_response.status_code == 404
