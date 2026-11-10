"""Bootstrap the first superadmin account, manually.

Umumnya tidak perlu lagi: `SUPERADMIN_*` / `ADMIN_*` di .env sudah bikin akun admin/superadmin
otomatis tiap backend-api start (lihat app/services/seed.py). Script ini disimpan
untuk kasus one-off — bikin superadmin tanpa menaruh passwordnya di .env:

    docker compose exec backend-api python scripts/seed_admin.py --email you@example.com --password ...

Beda perilaku dengan seeder otomatis: script ini MENOLAK kalau emailnya sudah ada,
sedangkan seeder otomatis akan menaikkan role akun tersebut.
"""
import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.database import SessionLocal  # noqa: E402
from app.models.user import User, UserRole  # noqa: E402
from app.services.auth import hash_password  # noqa: E402


def seed_admin(email: str, password: str, name: str) -> None:
    db = SessionLocal()
    try:
        existing = db.query(User).filter(User.email == email).first()
        if existing is not None:
            print(f"User {email} already exists (role={existing.role.value}) — not creating a duplicate.")
            sys.exit(1)

        user = User(
            email=email,
            name=name,
            password_hash=hash_password(password),
            role=UserRole.superadmin,
        )
        db.add(user)
        db.commit()
        print(f"Created superadmin: {email}")
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed the first superadmin account.")
    parser.add_argument("--email", default=os.environ.get("SEED_ADMIN_EMAIL"))
    parser.add_argument("--password", default=os.environ.get("SEED_ADMIN_PASSWORD"))
    parser.add_argument("--name", default=os.environ.get("SEED_ADMIN_NAME", "Superadmin"))
    args = parser.parse_args()

    if not args.email or not args.password:
        parser.error("--email and --password are required (or set SEED_ADMIN_EMAIL / SEED_ADMIN_PASSWORD)")

    seed_admin(args.email, args.password, args.name)


if __name__ == "__main__":
    main()
