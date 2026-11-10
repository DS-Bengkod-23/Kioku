"""Seeder akun admin & superadmin dari env.

Dijalankan otomatis oleh entrypoint backend-api setiap container start (lihat
`backend/Dockerfile.api`), sesudah `alembic upgrade head` dan sebelum uvicorn —
jadi tidak perlu lagi `docker compose exec ... scripts/seed_admin.py` manual.

Env yang dipakai (semuanya opsional, kosong = dilewati):

    SUPERADMIN_EMAIL / SUPERADMIN_PASSWORD
    ADMIN_EMAIL      / ADMIN_PASSWORD

Idempotent, dan sengaja konservatif terhadap akun yang sudah ada:
  - email belum ada        -> akun dibuat
  - email sudah ada        -> password TIDAK PERNAH ditimpa
  - role existing < target -> dinaikkan (+ dicatat ke AuditLog, actor sistem)
  - role existing >= target -> dibiarkan (seeder tidak pernah menurunkan role)
"""
import sys
from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.config import settings
from app.database import SessionLocal
from app.models.audit_log import AuditAction, AuditLog
from app.models.user import ROLE_RANK, AuthProvider, User, UserRole
from app.services.auth import hash_password


@dataclass(frozen=True)
class SeedAccount:
    email: str
    password: str
    role: UserRole
    name: str


def accounts_from_settings(cfg=settings) -> list[SeedAccount]:
    """Bangun daftar akun dari env. Email + password harus terisi dua-duanya;
    kalau hanya salah satu, pasangan itu dilewati dengan peringatan (bukan error)."""
    pairs = [
        # superadmin duluan: kalau email-nya sama dengan admin, role tertinggi yang menang
        ("SUPERADMIN", cfg.SUPERADMIN_EMAIL, cfg.SUPERADMIN_PASSWORD, UserRole.superadmin, "Super Admin"),
        ("ADMIN", cfg.ADMIN_EMAIL, cfg.ADMIN_PASSWORD, UserRole.admin, "Admin"),
    ]

    accounts: list[SeedAccount] = []
    for prefix, email, password, role, name in pairs:
        email = email.strip().lower()
        password = password.strip()

        if not email and not password:
            continue  # tidak diisi, memang tidak ingin di-seed

        if not email or not password:
            print(
                f"[seed] {prefix} dilewati: {prefix}_EMAIL dan {prefix}_PASSWORD "
                "harus diisi dua-duanya.",
                file=sys.stderr,
            )
            continue

        accounts.append(SeedAccount(email=email, password=password, role=role, name=name))

    return accounts


def seed_accounts(db: Session, accounts: list[SeedAccount]) -> None:
    for account in accounts:
        existing = db.query(User).filter(User.email == account.email).first()

        if existing is None:
            db.add(
                User(
                    email=account.email,
                    name=account.name,
                    password_hash=hash_password(account.password),
                    role=account.role,
                    auth_provider=AuthProvider.local,
                )
            )
            db.commit()
            print(f"[seed] dibuat: {account.email} (role={account.role.value})")
            continue

        if ROLE_RANK[existing.role] >= ROLE_RANK[account.role]:
            print(
                f"[seed] dilewati: {account.email} sudah ada "
                f"(role={existing.role.value}, password tidak ditimpa)"
            )
            continue

        old_role = existing.role
        existing.role = account.role
        db.add(
            AuditLog(
                actor_id=None,  # aksi sistem, bukan superadmin tertentu
                action=AuditAction.promote_user,
                target_type="user",
                target_id=existing.id,
                reason=(
                    f"auto-seed from env: role changed from "
                    f"{old_role.value} to {account.role.value}"
                ),
            )
        )
        db.commit()
        print(
            f"[seed] dinaikkan: {account.email} {old_role.value} -> {account.role.value} "
            "(password tidak ditimpa)"
        )


def run_seed_from_settings() -> None:
    accounts = accounts_from_settings()
    if not accounts:
        print("[seed] SUPERADMIN_*/ADMIN_* kosong — tidak ada akun yang di-seed.")
        return

    db = SessionLocal()
    try:
        seed_accounts(db, accounts)
    finally:
        db.close()


def main() -> None:
    try:
        run_seed_from_settings()
    except Exception as exc:  # noqa: BLE001 — seeder tidak boleh memblokir startup
        print(f"[seed] DILEWATI karena error tak terduga: {exc!r}", file=sys.stderr)


if __name__ == "__main__":
    main()
