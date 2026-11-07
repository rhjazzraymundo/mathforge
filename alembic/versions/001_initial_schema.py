"""initial schema — users, attempts, mastery, review_queue

Revision ID: 001_initial
Revises: (root)
Create Date: 2026-11-07
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "attempts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("topic", sa.String(50), nullable=False),
        sa.Column("difficulty", sa.Integer(), nullable=False),
        sa.Column("is_correct", sa.Boolean(), nullable=False),
        sa.Column("user_answer", sa.Text()),
        sa.Column("correct_answer", sa.Text()),
        sa.Column("error_tag", sa.String(50)),
        sa.Column("time_taken_ms", sa.Integer()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_attempts_user_topic", "attempts", ["user_id", "topic"])
    op.create_index("ix_attempts_created", "attempts", ["created_at"])

    op.create_table(
        "mastery",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("topic", sa.String(50), primary_key=True),
        sa.Column("current_level", sa.Integer(), server_default="1"),
        sa.Column("recent_results", sa.JSON(), server_default="[]"),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "review_queue",
        sa.Column("user_id", sa.Uuid(), sa.ForeignKey("users.id"), primary_key=True),
        sa.Column("topic", sa.String(50), primary_key=True),
        sa.Column("difficulty", sa.Integer(), primary_key=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("interval_days", sa.Integer(), server_default="1"),
    )


def downgrade() -> None:
    op.drop_table("review_queue")
    op.drop_table("mastery")
    op.drop_index("ix_attempts_created", table_name="attempts")
    op.drop_index("ix_attempts_user_topic", table_name="attempts")
    op.drop_table("attempts")
    op.drop_table("users")

