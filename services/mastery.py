"""Mastery-ladder service.

Core rule: "8 of 10 correct at the current level → level up."

The promotion logic is a **pure function** (``check_promotion``) that
is easy to test without a database.  ``record_attempt`` orchestrates
persistence around that pure core.
"""

import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

# --- Tuning knobs -----------------------------------------------------------

REQUIRED_TOTAL = 10   # student must have at least this many attempts …
REQUIRED_CORRECT = 8  # … with at least this many correct → promote


# --- Data transfer object ---------------------------------------------------

@dataclass
class MasteryStatus:
    """Returned after every attempt so the UI can update immediately."""
    topic: str
    current_level: int
    recent_results: list[bool]
    promoted: bool = False

    @property
    def recent_correct(self) -> int:
        return sum(self.recent_results)

    @property
    def recent_total(self) -> int:
        return len(self.recent_results)


# --- Pure promotion logic (no DB) -------------------------------------------

def check_promotion(
    current_level: int,
    recent_results: list[bool],
    new_result: bool,
    at_difficulty: int,
) -> tuple[int, list[bool], bool]:
    """Decide whether to promote.

    Returns ``(new_level, new_results, promoted)``.

    Only updates the sliding window when *at_difficulty* matches
    *current_level* — answering at a different difficulty is still
    logged in ``attempts`` but doesn't affect the mastery ladder.
    """
    if at_difficulty != current_level:
        return current_level, recent_results, False

    # Append and keep only the last REQUIRED_TOTAL entries.
    results = (recent_results + [new_result])[-REQUIRED_TOTAL:]

    if len(results) >= REQUIRED_TOTAL and sum(results) >= REQUIRED_CORRECT:
        # 🎉 Level up — reset the window for the next level.
        return current_level + 1, [], True

    return current_level, results, False


# --- Orchestrator (DB + pure logic) ------------------------------------------

def record_attempt(
    session: Session,
    user_id: uuid.UUID,
    topic: str,
    difficulty: int,
    is_correct: bool,
    user_answer: str,
    correct_answer: str,
    error_tag: str | None = None,
    time_taken_ms: int | None = None,
) -> MasteryStatus:
    """Save an attempt **and** update the mastery ladder in one transaction.

    Returns a :class:`MasteryStatus` snapshot the UI can display right away.
    """
    from db import repositories as repo

    # 1. Log the attempt (always, regardless of difficulty vs level).
    repo.save_attempt(
        session,
        user_id=user_id,
        topic=topic,
        difficulty=difficulty,
        is_correct=is_correct,
        user_answer=user_answer,
        correct_answer=correct_answer,
        error_tag=error_tag,
        time_taken_ms=time_taken_ms,
    )

    # 2. Fetch (or create) the mastery record.
    mastery = repo.get_or_create_mastery(session, user_id, topic)
    current_results = list(mastery.recent_results) if mastery.recent_results else []

    # 3. Pure promotion check.
    new_level, new_results, promoted = check_promotion(
        mastery.current_level, current_results, is_correct, difficulty,
    )

    # 4. Persist any changes.
    #    Assign a *new* list (don't mutate in-place) so SQLAlchemy's
    #    change-detection picks it up for the JSON column.
    mastery.current_level = new_level
    mastery.recent_results = new_results
    mastery.updated_at = datetime.now(timezone.utc)
    session.commit()

    return MasteryStatus(
        topic=topic,
        current_level=new_level,
        recent_results=new_results,
        promoted=promoted,
    )

