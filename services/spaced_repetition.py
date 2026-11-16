"""Spaced-repetition service.

Interval schedule:  1 → 3 → 7 → graduated (removed from queue).

Rules:
  • Wrong answer on ANY problem → reset/add to queue at 1-day interval.
  • Correct answer on a queued problem → advance to next interval.
  • Correct answer on a NON-queued problem → no-op.

Like the mastery service, the scheduling logic is a **pure function**
(``next_review_state``) that is easy to test without a database.
``update_review`` orchestrates persistence around that pure core.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

# Increasing intervals (in days).  After passing the last one,
# the item is "graduated" and removed from the review queue.
INTERVALS = [1, 3, 7]


# --- Pure logic (no DB) -----------------------------------------------------

@dataclass
class ReviewAction:
    """What should happen to a review-queue entry after an answer."""
    should_exist: bool       # True → upsert, False → delete
    interval_days: int = 1   # only meaningful when should_exist=True
    graduated: bool = False  # True → item was removed because all intervals passed


def next_review_state(
    is_correct: bool,
    current_interval: int | None,
) -> ReviewAction:
    """Decide what should happen to the review entry.

    Parameters
    ----------
    is_correct : bool
        Whether the student answered correctly.
    current_interval : int or None
        The current ``interval_days`` of the review-queue row,
        or ``None`` if the (topic, difficulty) is not in the queue.

    Returns
    -------
    ReviewAction
        Describes whether the entry should exist, at what interval,
        and whether the student graduated.
    """
    if not is_correct:
        # Wrong → always (re)schedule at the shortest interval.
        return ReviewAction(should_exist=True, interval_days=INTERVALS[0])

    if current_interval is None:
        # Correct AND not in queue → nothing to do.
        return ReviewAction(should_exist=False)

    # Correct AND in the queue → advance to the next interval.
    next_interval = _next_interval_after(current_interval)
    if next_interval is None:
        # Passed the longest interval → graduated!
        return ReviewAction(should_exist=False, graduated=True)
    return ReviewAction(should_exist=True, interval_days=next_interval)


def _next_interval_after(current: int) -> int | None:
    """Return the next interval after *current*, or ``None`` if graduated.

    Works even if *current* is not exactly in INTERVALS (finds the first
    interval strictly greater than *current*).
    """
    for iv in INTERVALS:
        if iv > current:
            return iv
    return None


# --- Orchestrator (DB + pure logic) -----------------------------------------

def update_review(
    session: Session,
    user_id: uuid.UUID,
    topic: str,
    difficulty: int,
    is_correct: bool,
    now: datetime | None = None,
) -> ReviewAction:
    """Update the review queue after an answer.  Flushes but does NOT commit.

    Parameters
    ----------
    now : datetime, optional
        Override "current time" for deterministic tests.

    Returns the :class:`ReviewAction` so the caller knows what happened.
    """
    from db import repositories as repo

    if now is None:
        now = datetime.now(timezone.utc)

    # What's the current state?
    existing = repo.get_review(session, user_id, topic, difficulty)
    current_interval = existing.interval_days if existing else None

    # Pure decision.
    action = next_review_state(is_correct, current_interval)

    # Persist.
    if action.should_exist:
        due_at = now + timedelta(days=action.interval_days)
        repo.upsert_review(
            session, user_id, topic, difficulty, due_at, action.interval_days,
        )
    elif existing is not None:
        repo.delete_review(session, user_id, topic, difficulty)

    return action

