import pytest

from app.models.user import User, UserRole
from scripts.seed_admin import seed_admin


def test_seed_admin_creates_superadmin(db_session):
    seed_admin("root@example.com", "supersecret", "Root Admin")

    user = db_session.query(User).filter(User.email == "root@example.com").one()
    assert user.role == UserRole.superadmin


def test_seed_admin_refuses_duplicate_email(db_session, make_user):
    make_user(email="dup@example.com")

    with pytest.raises(SystemExit):
        seed_admin("dup@example.com", "whatever", "Someone")
