"""add structured location fields to meetings

Revision ID: a2b3c4d5e6f7
Revises: f6a7b8c9d0e1
Create Date: 2026-07-09

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "a2b3c4d5e6f7"
down_revision: Union[str, None] = "f6a7b8c9d0e1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("meetings", sa.Column("location_building", sa.String(200), nullable=True))
    op.add_column("meetings", sa.Column("location_room", sa.String(200), nullable=True))
    op.add_column("meetings", sa.Column("location_city", sa.String(200), nullable=True))


def downgrade() -> None:
    op.drop_column("meetings", "location_city")
    op.drop_column("meetings", "location_room")
    op.drop_column("meetings", "location_building")
