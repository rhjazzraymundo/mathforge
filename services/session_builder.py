"""Daily-session builder.

Assembles a list of ~10 problems mixing:
  1. **Due reviews** — topics/difficulties the student missed before.
  2. **New problems** — spread across topics at the student's current
     mastery level.

The builder is a regular function (not a generator) so the UI can
show "Problem 3 of 10" up front.
"""

import random
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from generators.models import Problem
from generators.registry import get_generator, list_topics

# Target session size.
TARGET_PROBLEMS = 10


@dataclass
class SessionItem:
    """One problem in a session, tagged as review or new."""
    problem: Problem
    is_review: bool


def build_session(
    db_session: Session,
    user_id: uuid.UUID,
    *,
    target: int = TARGET_PROBLEMS,
    now: datetime | None = None,
    seed: int | None = None,
) -> list[SessionItem]:
    """Return a shuffled list of up to *target* :class:`SessionItem`\\s.

    Parameters
    ----------
    db_session : Session
        Open SQLAlchemy session.
    user_id : uuid.UUID
        Who is practising.
    target : int
        How many problems to include (default 10).
    now : datetime, optional
        Override "current time" (for tests).
    seed : int, optional
        Seed for the problem RNG (for reproducible tests).
        If ``None``, uses the current timestamp so each session is unique.
    """
    from db import repositories as repo

    if now is None:
        now = datetime.now(timezone.utc)
    if seed is None:
        seed = int(now.timestamp() * 1000)

    items: list[SessionItem] = []
    rng_counter = 0  # incremented per problem for unique seeds

    # ------------------------------------------------------------------
    # 1. Due reviews
    # ------------------------------------------------------------------
    due = repo.get_due_reviews(db_session, user_id, as_of=now)
    for review in due:
        if len(items) >= target:
            break
        try:
            gen = get_generator(review.topic)
        except KeyError:
            continue  # topic removed from registry — skip
        problem = gen(review.difficulty, random.Random(seed + rng_counter))
        rng_counter += 1
        items.append(SessionItem(problem=problem, is_review=True))

    # ------------------------------------------------------------------
    # 2. Fill with new problems at the user's mastery level
    # ------------------------------------------------------------------
    remaining = target - len(items)
    if remaining > 0:
        # Build a map of topic → current mastery level (default 1).
        mastery_map: dict[str, int] = {}
        for m in repo.get_all_mastery(db_session, user_id):
            mastery_map[m.topic] = m.current_level

        topics = list_topics()
        if not topics:
            return items  # no topics registered — shouldn't happen

        # Round-robin across topics so the session is varied.
        for i in range(remaining):
            topic = topics[i % len(topics)]
            level = min(mastery_map.get(topic, 1), 5)  # cap at max difficulty
            gen = get_generator(topic)
            problem = gen(level, random.Random(seed + rng_counter))
            rng_counter += 1
            items.append(SessionItem(problem=problem, is_review=False))

    # ------------------------------------------------------------------
    # 3. Shuffle so reviews aren't always first
    # ------------------------------------------------------------------
    shuffle_rng = random.Random(seed)
    shuffle_rng.shuffle(items)

    return items

