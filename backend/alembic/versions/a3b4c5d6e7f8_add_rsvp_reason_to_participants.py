"""add rsvp_reason to meeting_participants

Revision ID: a3b4c5d6e7f8
Revises: f3a4b5c6d7e8
Create Date: 2026-07-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a3b4c5d6e7f8"
down_revision: Union[str, None] = "f3a4b5c6d7e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "meeting_participants",
        sa.Column("rsvp_reason", sa.Text(), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("meeting_participants", "rsvp_reason")
