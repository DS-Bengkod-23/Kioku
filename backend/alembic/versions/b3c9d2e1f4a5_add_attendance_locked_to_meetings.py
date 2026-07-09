"""add attendance_locked to meetings

Revision ID: b3c9d2e1f4a5
Revises: 9a7befed844a
Create Date: 2026-06-27

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "b3c9d2e1f4a5"
down_revision: Union[str, None] = "9a7befed844a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "meetings",
        sa.Column("attendance_locked", sa.Boolean(), nullable=False, server_default="false"),
    )


def downgrade() -> None:
    op.drop_column("meetings", "attendance_locked")
