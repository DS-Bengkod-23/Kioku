"""add avatar to users

Revision ID: e2f3a4b5c6d7
Revises: c9d0e1f2a3b4
Create Date: 2026-07-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "e2f3a4b5c6d7"
down_revision: Union[str, None] = "c9d0e1f2a3b4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("avatar_object_key", sa.String(500), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "avatar_object_key")
