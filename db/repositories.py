"""Thin data-access helpers (repository pattern).

Each function receives an open Session and returns ORM objects.
They call ``flush()`` — not ``commit()`` — so the service layer
controls the transaction boundary.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import User, Attempt, Mastery, ReviewQueue

# Fixed id for the single anonymous user (MVP).
# Keeping user_id in the schema means we can add auth later
# without migrating existing data.
DEFAULT_USER_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def get_or_create_default_user(session: Session) -> User:
    """Return the anonymous default user, creating it on first call."""
    user = session.get(User, DEFAULT_USER_ID)
    if user is None:
        user = User(id=DEFAULT_USER_ID)
        session.add(user)
        session.commit()
    return user


def save_attempt(
    session: Session,
    *,
    user_id: uuid.UUID,
    topic: str,
    difficulty: int,
    is_correct: bool,
    user_answer: str,
    correct_answer: str,
    error_tag: str | None = None,
    time_taken_ms: int | None = None,
) -> Attempt:
    """Insert an attempt row.  Flushes but does NOT commit."""
    attempt = Attempt(
        user_id=user_id,
        topic=topic,
        difficulty=difficulty,
        is_correct=is_correct,
        user_answer=user_answer,
        correct_answer=correct_answer,
        error_tag=error_tag,
        time_taken_ms=time_taken_ms,
    )
    session.add(attempt)
    session.flush()
    return attempt


def get_or_create_mastery(session: Session, user_id: uuid.UUID, topic: str) -> Mastery:
    """Return the mastery record for (user, topic), creating a level-1
    record if none exists yet."""
    mastery = session.get(Mastery, (user_id, topic))
    if mastery is None:
        mastery = Mastery(user_id=user_id, topic=topic)
        session.add(mastery)
        session.flush()
    return mastery


def get_all_mastery(session: Session, user_id: uuid.UUID) -> list[Mastery]:
    """Return every mastery record for a user (one per topic they've tried)."""
    stmt = select(Mastery).where(Mastery.user_id == user_id)
    return list(session.scalars(stmt))


# ---------------------------------------------------------------------------
# ReviewQueue helpers (Phase 3)
# ---------------------------------------------------------------------------

def upsert_review(
    session: Session,
    user_id: uuid.UUID,
    topic: str,
    difficulty: int,
    due_at: datetime,
    interval_days: int,
) -> ReviewQueue:
    """Insert or update a review-queue entry.  Flushes but does NOT commit."""
    review = session.get(ReviewQueue, (user_id, topic, difficulty))
    if review is None:
        review = ReviewQueue(
            user_id=user_id, topic=topic, difficulty=difficulty,
            due_at=due_at, interval_days=interval_days,
        )
        session.add(review)
    else:
        review.due_at = due_at
        review.interval_days = interval_days
    session.flush()
    return review


def delete_review(
    session: Session, user_id: uuid.UUID, topic: str, difficulty: int,
) -> bool:
    """Remove a review entry.  Returns True if a row was deleted."""
    review = session.get(ReviewQueue, (user_id, topic, difficulty))
    if review is not None:
        session.delete(review)
        session.flush()
        return True
    return False


def get_review(
    session: Session, user_id: uuid.UUID, topic: str, difficulty: int,
) -> ReviewQueue | None:
    """Fetch a single review entry (or None)."""
    return session.get(ReviewQueue, (user_id, topic, difficulty))


def get_due_reviews(
    session: Session, user_id: uuid.UUID, as_of: datetime | None = None,
) -> list[ReviewQueue]:
    """Return all review entries that are due on or before *as_of*."""
    if as_of is None:
        as_of = datetime.now(timezone.utc)
    stmt = (
        select(ReviewQueue)
        .where(ReviewQueue.user_id == user_id, ReviewQueue.due_at <= as_of)
        .order_by(ReviewQueue.due_at)
    )
    return list(session.scalars(stmt))

