"""SQLAlchemy ORM models for MathForge.

Four tables (see Phase 0 ER diagram):
  users         — one row per player (single anon user for MVP)
  attempts      — every answered problem
  mastery       — per-topic level + sliding window of recent results
  review_queue  — spaced-repetition schedule (Phase 3)

Design notes
------------
* Uses SQLAlchemy 2.x ``Mapped`` / ``mapped_column`` style.
* ``sa.Uuid`` is dialect-agnostic: native UUID on Postgres, CHAR(32) on
  SQLite — so the same models work in production and in-memory tests.
* Composite primary keys on ``mastery`` and ``review_queue`` because the
  natural key IS the identity (no surrogate id needed).
"""

import uuid
from datetime import datetime, timezone

import sqlalchemy as sa
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """Shared base for all ORM models."""
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4,
    )
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, primary_key=True, default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id"), nullable=False,
    )
    topic: Mapped[str] = mapped_column(sa.String(50), nullable=False)
    difficulty: Mapped[int] = mapped_column(sa.Integer, nullable=False)
    is_correct: Mapped[bool] = mapped_column(sa.Boolean, nullable=False)
    user_answer: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    correct_answer: Mapped[str | None] = mapped_column(sa.Text, nullable=True)
    error_tag: Mapped[str | None] = mapped_column(sa.String(50), nullable=True)
    time_taken_ms: Mapped[int | None] = mapped_column(sa.Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class Mastery(Base):
    """One row per (user, topic).  Tracks current level and a sliding
    window of the last 10 results at that level."""
    __tablename__ = "mastery"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id"), primary_key=True,
    )
    topic: Mapped[str] = mapped_column(sa.String(50), primary_key=True)
    current_level: Mapped[int] = mapped_column(sa.Integer, default=1)
    # JSON list of booleans, e.g. [true, true, false, true, …]
    recent_results: Mapped[list] = mapped_column(sa.JSON, default=list)
    updated_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )


class ReviewQueue(Base):
    """Spaced-repetition schedule.  One row per (user, topic, difficulty)
    that is due for review.  Populated in Phase 3."""
    __tablename__ = "review_queue"

    user_id: Mapped[uuid.UUID] = mapped_column(
        sa.Uuid, sa.ForeignKey("users.id"), primary_key=True,
    )
    topic: Mapped[str] = mapped_column(sa.String(50), primary_key=True)
    difficulty: Mapped[int] = mapped_column(sa.Integer, primary_key=True)
    due_at: Mapped[datetime] = mapped_column(
        sa.DateTime(timezone=True), nullable=False,
    )
    interval_days: Mapped[int] = mapped_column(sa.Integer, default=1)

