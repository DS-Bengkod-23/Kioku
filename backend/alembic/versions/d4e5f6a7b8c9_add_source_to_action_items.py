"""add source to action_items

Revision ID: d4e5f6a7b8c9
Revises: a1b2c3d4e5f6
Create Date: 2026-07-03

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d4e5f6a7b8c9"
down_revision: Union[str, None] = "a1b2c3d4e5f6"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    postgresql.ENUM("ai", "manual", name="actionitemsource").create(op.get_bind(), checkfirst=True)
    op.add_column(
        "action_items",
        sa.Column(
            "source",
            postgresql.ENUM("ai", "manual", name="actionitemsource", create_type=False),
            nullable=False,
            server_default="ai",
        ),
    )


def downgrade() -> None:
    op.drop_column("action_items", "source")
    postgresql.ENUM(name="actionitemsource").drop(op.get_bind(), checkfirst=True)
