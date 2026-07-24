"""add soft delete to meetings and recordings

Revision ID: c9d0e1f2a3b4
Revises: b8c9d0e1f2a3
Create Date: 2026-07-20

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "c9d0e1f2a3b4"
down_revision: Union[str, None] = "b8c9d0e1f2a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "meetings",
        sa.Column(
            "deleted_by_admin_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    op.add_column("recordings", sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column(
        "recordings",
        sa.Column(
            "deleted_by_admin_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_column("recordings", "deleted_by_admin_id")
    op.drop_column("recordings", "deleted_at")
    op.drop_column("meetings", "deleted_by_admin_id")
    op.drop_column("meetings", "deleted_at")
