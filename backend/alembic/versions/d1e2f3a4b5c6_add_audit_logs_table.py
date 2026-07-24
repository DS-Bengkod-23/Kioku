"""add audit_logs table

Revision ID: d1e2f3a4b5c6
Revises: c7d8e9f0a1b2
Create Date: 2026-07-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "c7d8e9f0a1b2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_AUDIT_ACTIONS = (
    "suspend_user",
    "unsuspend_user",
    "promote_user",
    "demote_user",
    "reset_password",
    "request_meeting_access",
    "delete_meeting",
    "delete_recording",
)


def upgrade() -> None:
    postgresql.ENUM(*_AUDIT_ACTIONS, name="auditaction").create(op.get_bind(), checkfirst=True)

    op.create_table(
        "audit_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "actor_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column(
            "action",
            postgresql.ENUM(*_AUDIT_ACTIONS, name="auditaction", create_type=False),
            nullable=False,
        ),
        sa.Column("target_type", sa.String(50), nullable=False),
        sa.Column("target_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("audit_logs")
    postgresql.ENUM(name="auditaction").drop(op.get_bind(), checkfirst=True)
