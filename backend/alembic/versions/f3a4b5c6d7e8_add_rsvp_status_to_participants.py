"""add rsvp_status to meeting_participants

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
Create Date: 2026-07-22

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    postgresql.ENUM("pending", "akan_hadir", "tidak_hadir", name="rsvpstatus").create(
        op.get_bind(), checkfirst=True
    )
    op.add_column(
        "meeting_participants",
        sa.Column(
            "rsvp_status",
            postgresql.ENUM("pending", "akan_hadir", "tidak_hadir", name="rsvpstatus", create_type=False),
            nullable=False,
            server_default="pending",
        ),
    )


def downgrade() -> None:
    op.drop_column("meeting_participants", "rsvp_status")
    postgresql.ENUM(name="rsvpstatus").drop(op.get_bind(), checkfirst=True)
