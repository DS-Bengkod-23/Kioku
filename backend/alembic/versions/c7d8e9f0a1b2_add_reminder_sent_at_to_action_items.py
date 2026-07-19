"""add reminder_sent_at to action_items

Revision ID: c7d8e9f0a1b2
Revises: 29f79ea4aacd
Create Date: 2026-07-19

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "c7d8e9f0a1b2"
down_revision: Union[str, None] = "29f79ea4aacd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "action_items",
        sa.Column("reminder_sent_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("action_items", "reminder_sent_at")
