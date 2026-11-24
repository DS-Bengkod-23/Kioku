"""add notulen review (draft/published status, versions table, AI review columns)

Revision ID: b4c5d6e7f8a9
Revises: a3b4c5d6e7f8
Create Date: 2026-11-24

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "b4c5d6e7f8a9"
down_revision: Union[str, None] = "a3b4c5d6e7f8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    postgresql.ENUM("draft", "published", name="notulenstatus").create(bind, checkfirst=True)
    postgresql.ENUM("ai", "published", name="notulenversionkind").create(bind, checkfirst=True)

    op.add_column(
        "meetings",
        sa.Column(
            "notulen_status",
            postgresql.ENUM("draft", "published", name="notulenstatus", create_type=False),
            nullable=True,
        ),
    )
    op.add_column(
        "meetings", sa.Column("notulen_edited_at", sa.DateTime(timezone=True), nullable=True)
    )
    op.add_column("action_items", sa.Column("ai_assignee_text", sa.Text(), nullable=True))
    op.add_column("action_items", sa.Column("ai_due_date_text", sa.Text(), nullable=True))

    op.create_table(
        "notulen_versions",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "meeting_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("meetings.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "kind",
            postgresql.ENUM("ai", "published", name="notulenversionkind", create_type=False),
            nullable=False,
        ),
        sa.Column("version", sa.Integer(), nullable=True),
        sa.Column("content", postgresql.JSONB(), nullable=False),
        sa.Column(
            "created_by",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("meeting_id", "version", name="uq_notulen_versions_meeting_version"),
    )
    op.create_index("ix_notulen_versions_meeting_id", "notulen_versions", ["meeting_id"])

    # Backfill (keputusan #13): notulen lama sudah terkirim -> published v1,
    # tanpa snapshot AI (action item-nya mungkin sudah diedit).
    op.execute(
        """
        UPDATE meetings SET notulen_status = 'published'
        WHERE id IN (SELECT meeting_id FROM summaries)
        """
    )
    op.execute(
        """
        INSERT INTO notulen_versions (id, meeting_id, kind, version, content, created_by, created_at)
        SELECT gen_random_uuid(), s.meeting_id, 'published', 1,
          jsonb_build_object(
            'tldr', s.tldr, 'decisions', s.decisions, 'topics', s.topics,
            'action_items', COALESCE((
              SELECT jsonb_agg(jsonb_build_object(
                'id', ai.id::text, 'task', ai.task,
                'assignee_participant_id', ai.assignee_participant_id::text,
                'assignee_name', COALESCE(u.name, mp.email),
                'due_date', ai.due_date::text) ORDER BY ai.id)
              FROM action_items ai
              LEFT JOIN meeting_participants mp ON mp.id = ai.assignee_participant_id
              LEFT JOIN users u ON u.id = mp.user_id
              WHERE ai.meeting_id = s.meeting_id), '[]'::jsonb)),
          m.organizer_id, now()
        FROM summaries s JOIN meetings m ON m.id = s.meeting_id
        """
    )


def downgrade() -> None:
    op.drop_index("ix_notulen_versions_meeting_id", table_name="notulen_versions")
    op.drop_table("notulen_versions")
    op.drop_column("action_items", "ai_due_date_text")
    op.drop_column("action_items", "ai_assignee_text")
    op.drop_column("meetings", "notulen_edited_at")
    op.drop_column("meetings", "notulen_status")
    postgresql.ENUM(name="notulenversionkind").drop(op.get_bind(), checkfirst=True)
    postgresql.ENUM(name="notulenstatus").drop(op.get_bind(), checkfirst=True)
