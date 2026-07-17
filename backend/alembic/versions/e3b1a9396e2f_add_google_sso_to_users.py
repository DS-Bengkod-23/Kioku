"""add google sso fields to users

Revision ID: e3b1a9396e2f
Revises: a2b3c4d5e6f7
Create Date: 2026-07-17

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "e3b1a9396e2f"
down_revision: Union[str, None] = "a2b3c4d5e6f7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    postgresql.ENUM("local", "google", name="authprovider").create(op.get_bind(), checkfirst=True)
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=True)
    op.add_column(
        "users",
        sa.Column(
            "auth_provider",
            postgresql.ENUM("local", "google", name="authprovider", create_type=False),
            nullable=False,
            server_default="local",
        ),
    )
    op.add_column("users", sa.Column("google_sub", sa.String(255), nullable=True))
    op.create_unique_constraint("uq_users_google_sub", "users", ["google_sub"])


def downgrade() -> None:
    op.drop_constraint("uq_users_google_sub", "users", type_="unique")
    op.drop_column("users", "google_sub")
    op.drop_column("users", "auth_provider")
    op.alter_column("users", "password_hash", existing_type=sa.String(255), nullable=False)
    postgresql.ENUM(name="authprovider").drop(op.get_bind(), checkfirst=True)
