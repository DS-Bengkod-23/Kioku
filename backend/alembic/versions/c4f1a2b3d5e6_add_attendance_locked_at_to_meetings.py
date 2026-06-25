"""add attendance_locked_at to meetings

Revision ID: c4f1a2b3d5e6
Revises: 9a7befed844a
Create Date: 2026-06-18

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c4f1a2b3d5e6"
down_revision: Union[str, None] = "9a7befed844a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "meetings",
        sa.Column("attendance_locked_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meetings", "attendance_locked_at")
