"""add role to users

Revision ID: a7b8c9d0e1f2
Revises: d1e2f3a4b5c6
Create Date: 2026-07-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a7b8c9d0e1f2"
down_revision: Union[str, None] = "d1e2f3a4b5c6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    postgresql.ENUM("user", "admin", "superadmin", name="userrole").create(op.get_bind(), checkfirst=True)
    op.add_column(
        "users",
        sa.Column(
            "role",
            postgresql.ENUM("user", "admin", "superadmin", name="userrole", create_type=False),
            nullable=False,
            server_default="user",
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "role")
    postgresql.ENUM(name="userrole").drop(op.get_bind(), checkfirst=True)
