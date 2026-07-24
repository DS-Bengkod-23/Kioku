from app.models.user import UserRole


def test_me_endpoint_exposes_role_for_frontend_nav_guard(client, make_user, auth_headers):
    admin = make_user(role=UserRole.admin)

    response = client.get("/api/v1/auth/me", headers=auth_headers(admin))

    assert response.status_code == 200
    assert response.json()["role"] == "admin"
