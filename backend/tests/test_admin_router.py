from app.models.user import UserRole


def test_regular_user_gets_403_on_admin_users_list(client, make_user, auth_headers):
    user = make_user(role=UserRole.user)
    response = client.get("/api/v1/admin/users", headers=auth_headers(user))
    assert response.status_code == 403


def test_regular_user_gets_403_on_admin_meetings_list(client, make_user, auth_headers):
    user = make_user(role=UserRole.user)
    response = client.get("/api/v1/admin/meetings", headers=auth_headers(user))
    assert response.status_code == 403


def test_admin_can_list_users(client, make_user, auth_headers):
    admin = make_user(role=UserRole.admin)
    make_user(role=UserRole.user)
    response = client.get("/api/v1/admin/users", headers=auth_headers(admin))
    assert response.status_code == 200
    assert len(response.json()) == 2


def test_superadmin_can_list_users(client, make_user, auth_headers):
    superadmin = make_user(role=UserRole.superadmin)
    response = client.get("/api/v1/admin/users", headers=auth_headers(superadmin))
    assert response.status_code == 200
    assert len(response.json()) == 1


def test_admin_can_list_meetings_empty(client, make_user, auth_headers):
    admin = make_user(role=UserRole.admin)
    response = client.get("/api/v1/admin/meetings", headers=auth_headers(admin))
    assert response.status_code == 200
    assert response.json() == []
