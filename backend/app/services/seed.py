"""Seeder akun admin/superadmin dari env `SEED_ACCOUNTS`.

Dijalankan otomatis oleh entrypoint backend-api setiap container start (lihat
`backend/Dockerfile.api`), sesudah `alembic upgrade head` dan sebelum uvicorn —
jadi tidak perlu lagi `docker compose exec ... scripts/seed_admin.py` manual.

Format `SEED_ACCOUNTS` (satu baris, akun dipisah `;`, field dipisah `|`):

    email|password|role|nama

`role` dan `nama` opsional (default `user`, dan nama diambil dari bagian depan
email). Password TIDAK boleh mengandung `|` atau `;`.

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

_ACCOUNT_SEPARATOR = ";"
_FIELD_SEPARATOR = "|"


@dataclass(frozen=True)
class SeedAccount:
    email: str
    password: str
    role: UserRole
    name: str


class SeedConfigError(ValueError):
    """SEED_ACCOUNTS salah format — dilempar sebelum menyentuh DB sama sekali."""


def parse_seed_accounts(raw: str) -> list[SeedAccount]:
    accounts: list[SeedAccount] = []
    seen_emails: set[str] = set()

    for index, chunk in enumerate(raw.split(_ACCOUNT_SEPARATOR), start=1):
        entry = chunk.strip()
        if not entry:
            continue  # toleransi trailing ';' atau spasi antar entri

        fields = [field.strip() for field in entry.split(_FIELD_SEPARATOR)]
        if len(fields) > 4:
            raise SeedConfigError(
                f"SEED_ACCOUNTS entri #{index}: kebanyakan field "
                f"(dapat {len(fields)}, maksimal 4). Format: email|password|role|nama"
            )

        fields += [""] * (4 - len(fields))
        email, password, role_raw, name = fields

        if not email or not password:
            raise SeedConfigError(
                f"SEED_ACCOUNTS entri #{index}: email dan password wajib diisi. "
                "Format: email|password|role|nama"
            )

        email = email.lower()
        if email in seen_emails:
            raise SeedConfigError(f"SEED_ACCOUNTS: email '{email}' muncul lebih dari sekali.")
        seen_emails.add(email)

        try:
            role = UserRole(role_raw) if role_raw else UserRole.user
        except ValueError:
            valid = ", ".join(r.value for r in UserRole)
            raise SeedConfigError(
                f"SEED_ACCOUNTS entri #{index}: role '{role_raw}' tidak dikenal (pilihan: {valid})."
            ) from None

        accounts.append(
            SeedAccount(
                email=email,
                password=password,
                role=role,
                name=name or email.split("@")[0],
            )
        )

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
                    f"auto-seed SEED_ACCOUNTS: role changed from "
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
    raw = settings.SEED_ACCOUNTS.strip()
    if not raw:
        print("[seed] SEED_ACCOUNTS kosong — tidak ada akun yang di-seed.")
        return

    accounts = parse_seed_accounts(raw)
    db = SessionLocal()
    try:
        seed_accounts(db, accounts)
    finally:
        db.close()


def main() -> None:
    try:
        run_seed_from_settings()
    except SeedConfigError as exc:
        # Salah ketik di .env tidak boleh bikin API gagal start — cukup diteriakin
        # di log, biar sisa aplikasi tetap jalan normal.
        print(f"[seed] DILEWATI karena konfigurasi tidak valid: {exc}", file=sys.stderr)
    except Exception as exc:  # noqa: BLE001 — seeder tidak boleh memblokir startup
        print(f"[seed] DILEWATI karena error tak terduga: {exc!r}", file=sys.stderr)


if __name__ == "__main__":
    main()
