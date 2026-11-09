import pytest

from app.models.audit_log import AuditAction, AuditLog
from app.models.user import AuthProvider, User, UserRole
from app.services.auth import verify_password
from app.services.seed import (
    SeedAccount,
    SeedConfigError,
    parse_seed_accounts,
    seed_accounts,
)


# --- parsing -------------------------------------------------------------


def test_parses_multiple_accounts_with_roles_and_names():
    accounts = parse_seed_accounts(
        "super@example.com|pw1|superadmin|Super Admin;admin@example.com|pw2|admin|Admin Kampus"
    )

    assert [(a.email, a.role, a.name) for a in accounts] == [
        ("super@example.com", UserRole.superadmin, "Super Admin"),
        ("admin@example.com", UserRole.admin, "Admin Kampus"),
    ]


def test_role_and_name_are_optional():
    (account,) = parse_seed_accounts("someone@example.com|pw")

    assert account.role == UserRole.user
    assert account.name == "someone"  # default dari bagian depan email


def test_tolerates_whitespace_trailing_separator_and_uppercase_email():
    accounts = parse_seed_accounts("  A@Example.com|pw|admin  ;  b@example.com|pw ; ")

    assert [a.email for a in accounts] == ["a@example.com", "b@example.com"]


@pytest.mark.parametrize(
    "raw",
    [
        "a@example.com|pw|bukanrole",  # role tidak dikenal
        "a@example.com",  # password kosong
        "|pw|admin",  # email kosong
        "a@example.com|pw|admin|Nama|kelebihan",  # kebanyakan field
        "a@example.com|pw;A@example.com|pw2",  # email duplikat (beda case)
    ],
)
def test_rejects_malformed_entries(raw):
    with pytest.raises(SeedConfigError):
        parse_seed_accounts(raw)


@pytest.mark.parametrize("raw", ["", "   ", " ; "])
def test_blank_input_yields_no_accounts(raw):
    assert parse_seed_accounts(raw) == []


# --- seeding -------------------------------------------------------------


def test_creates_missing_account(db_session):
    seed_accounts(
        db_session,
        [SeedAccount("new@example.com", "supersecret", UserRole.superadmin, "Root")],
    )

    user = db_session.query(User).filter(User.email == "new@example.com").one()
    assert user.role == UserRole.superadmin
    assert user.name == "Root"
    assert user.auth_provider == AuthProvider.local
    assert verify_password("supersecret", user.password_hash)


def test_never_overwrites_existing_password(db_session, make_user):
    make_user(email="existing@example.com", password="password-lama", role=UserRole.admin)

    seed_accounts(
        db_session,
        [SeedAccount("existing@example.com", "password-baru", UserRole.admin, "Ganti")],
    )

    user = db_session.query(User).filter(User.email == "existing@example.com").one()
    assert verify_password("password-lama", user.password_hash)
    assert user.name == "Test User"  # nama existing juga tidak ditimpa


def test_promotes_existing_lower_role_and_writes_audit_log(db_session, make_user):
    existing = make_user(email="promote@example.com", role=UserRole.user)

    seed_accounts(
        db_session,
        [SeedAccount("promote@example.com", "pw", UserRole.superadmin, "Root")],
    )

    db_session.refresh(existing)
    assert existing.role == UserRole.superadmin

    log = db_session.query(AuditLog).filter(AuditLog.target_id == existing.id).one()
    assert log.action == AuditAction.promote_user
    assert log.actor_id is None  # aksi sistem, bukan superadmin tertentu


def test_never_demotes_existing_higher_role(db_session, make_user):
    existing = make_user(email="boss@example.com", role=UserRole.superadmin)

    seed_accounts(db_session, [SeedAccount("boss@example.com", "pw", UserRole.user, "Boss")])

    db_session.refresh(existing)
    assert existing.role == UserRole.superadmin
    assert db_session.query(AuditLog).count() == 0


def test_is_idempotent_across_repeated_runs(db_session):
    accounts = [SeedAccount("repeat@example.com", "pw", UserRole.admin, "Repeat")]

    seed_accounts(db_session, accounts)
    seed_accounts(db_session, accounts)

    assert db_session.query(User).filter(User.email == "repeat@example.com").count() == 1
    assert db_session.query(AuditLog).count() == 0
