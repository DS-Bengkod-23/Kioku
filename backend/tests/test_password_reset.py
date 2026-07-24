from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi import HTTPException
from jose import jwt

from app.config import settings
from app.models.audit_log import AuditAction, AuditLog
from app.models.user import AuthProvider, User, UserRole
from app.services import admin as admin_service
from app.services.auth import (
    create_access_token,
    create_password_reset_token,
    verify_password,
)


def test_trigger_password_reset_sends_email_and_logs(db_session, make_user):
    superadmin = make_user(role=UserRole.superadmin)
    target = make_user(role=UserRole.user)

    # This backend's .env points SMTP at a real Gmail account, not Mailhog —
    # never let a test actually call out over SMTP.
    with patch("app.services.admin.send_password_reset_email") as mock_send:
        admin_service.trigger_password_reset(db_session, superadmin, target.id)

    mock_send.assert_called_once()
    assert mock_send.call_args.args[0] == target.email

    log = db_session.query(AuditLog).filter(AuditLog.target_id == target.id).one()
    assert log.action == AuditAction.reset_password
    assert log.actor_id == superadmin.id


def test_trigger_password_reset_rejects_google_only_account(db_session, make_user):
    superadmin = make_user(role=UserRole.superadmin)
    google_user = User(
        email="google-only@example.com",
        name="Google User",
        password_hash=None,
        auth_provider=AuthProvider.google,
        google_sub="google-sub-123",
    )
    db_session.add(google_user)
    db_session.commit()
    db_session.refresh(google_user)

    with pytest.raises(HTTPException) as exc_info:
        admin_service.trigger_password_reset(db_session, superadmin, google_user.id)
    assert exc_info.value.status_code == 400


def test_admin_cannot_trigger_password_reset(client, make_user, auth_headers):
    admin = make_user(role=UserRole.admin)
    target = make_user(role=UserRole.user)

    response = client.post(f"/api/v1/admin/users/{target.id}/reset-password", headers=auth_headers(admin))
    assert response.status_code == 403


def test_reset_token_confirm_updates_password(client, db_session, make_user):
    user = make_user(password="oldpassword123")
    token = create_password_reset_token(user.id)

    response = client.post(
        "/api/v1/auth/reset-password/confirm",
        json={"token": token, "new_password": "newpassword456"},
    )
    assert response.status_code == 200

    db_session.refresh(user)
    assert verify_password("newpassword456", user.password_hash)
    assert not verify_password("oldpassword123", user.password_hash)


def test_wrong_purpose_token_rejected(client, make_user):
    user = make_user()
    login_token = create_access_token({"sub": str(user.id)})  # right sub, wrong purpose

    response = client.post(
        "/api/v1/auth/reset-password/confirm",
        json={"token": login_token, "new_password": "whatever12345"},
    )
    assert response.status_code == 400


def test_expired_reset_token_rejected(client, make_user):
    user = make_user()
    expired_token = jwt.encode(
        {
            "sub": str(user.id),
            "purpose": "password_reset",
            "exp": datetime.now(timezone.utc) - timedelta(minutes=1),
        },
        settings.JWT_SECRET_KEY,
        algorithm="HS256",
    )

    response = client.post(
        "/api/v1/auth/reset-password/confirm",
        json={"token": expired_token, "new_password": "whatever12345"},
    )
    assert response.status_code == 400
