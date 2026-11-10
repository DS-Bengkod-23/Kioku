from types import SimpleNamespace

from app.models.audit_log import AuditAction, AuditLog
from app.models.user import AuthProvider, User, UserRole
from app.services.auth import verify_password
from app.services.seed import (
    SeedAccount,
    accounts_from_settings,
    seed_accounts,
)


# --- membaca env ---------------------------------------------------------


def _cfg(**overrides) -> SimpleNamespace:
    values = {
        "SUPERADMIN_EMAIL": "",
        "SUPERADMIN_PASSWORD": "",
        "ADMIN_EMAIL": "",
        "ADMIN_PASSWORD": "",
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def test_builds_superadmin_and_admin_from_env():
    accounts = accounts_from_settings(
        _cfg(
            SUPERADMIN_EMAIL="super@example.com",
            SUPERADMIN_PASSWORD="pw1",
            ADMIN_EMAIL="admin@example.com",
            ADMIN_PASSWORD="pw2",
        )
    )

    assert [(a.email, a.role) for a in accounts] == [
        ("super@example.com", UserRole.superadmin),
        ("admin@example.com", UserRole.admin),
    ]


def test_all_blank_yields_no_accounts():
    assert accounts_from_settings(_cfg()) == []


def test_only_superadmin_filled_skips_admin():
    accounts = accounts_from_settings(
        _cfg(SUPERADMIN_EMAIL="super@example.com", SUPERADMIN_PASSWORD="pw")
    )

    assert [a.role for a in accounts] == [UserRole.superadmin]


def test_strips_whitespace_and_lowercases_email():
    (account,) = accounts_from_settings(
        _cfg(ADMIN_EMAIL="  Admin@Example.COM ", ADMIN_PASSWORD="  pw  ")
    )

    assert account.email == "admin@example.com"
    assert account.password == "pw"


def test_half_filled_pair_is_skipped_not_fatal(capsys):
    accounts = accounts_from_settings(
        _cfg(
            SUPERADMIN_EMAIL="super@example.com",  # password lupa diisi
            ADMIN_EMAIL="admin@example.com",
            ADMIN_PASSWORD="pw",
        )
    )

    assert [a.role for a in accounts] == [UserRole.admin]
    assert "SUPERADMIN dilewati" in capsys.readouterr().err


def test_password_may_contain_any_character():
    (account,) = accounts_from_settings(
        _cfg(ADMIN_EMAIL="admin@example.com", ADMIN_PASSWORD="p|a;ss w0rd")
    )

    assert account.password == "p|a;ss w0rd"


def test_same_email_for_both_roles_superadmin_wins(db_session):
    accounts = accounts_from_settings(
        _cfg(
            SUPERADMIN_EMAIL="same@example.com",
            SUPERADMIN_PASSWORD="pw",
            ADMIN_EMAIL="same@example.com",
            ADMIN_PASSWORD="pw",
        )
    )

    seed_accounts(db_session, accounts)

    user = db_session.query(User).filter(User.email == "same@example.com").one()
    assert user.role == UserRole.superadmin


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
