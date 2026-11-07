"""Thin data-access helpers (repository pattern).

Each function receives an open Session and returns ORM objects.
They call ``flush()`` — not ``commit()`` — so the service layer
controls the transaction boundary.
"""

import uuid

from sqlalchemy.orm import Session

from db.models import User, Attempt, Mastery

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
    from sqlalchemy import select
    stmt = select(Mastery).where(Mastery.user_id == user_id)
    return list(session.scalars(stmt))

