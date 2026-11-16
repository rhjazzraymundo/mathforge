"""Tests for the session builder.

Exercises the session assembly logic with an in-memory SQLite database.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from services.session_builder import build_session, SessionItem, TARGET_PROBLEMS
from services.spaced_repetition import update_review
from db.repositories import DEFAULT_USER_ID


NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)
SEED = 42


class TestBuildSession:
    """Test session assembly."""

    def test_empty_session_all_new(self, db_session, default_user):
        """No reviews due → all items are new problems."""
        items = build_session(
            db_session, DEFAULT_USER_ID, now=NOW, seed=SEED,
        )
        assert len(items) == TARGET_PROBLEMS
        assert all(isinstance(it, SessionItem) for it in items)
        # No reviews → every item is new
        assert all(not it.is_review for it in items)

    def test_session_has_target_count(self, db_session, default_user):
        """Session has exactly TARGET_PROBLEMS items by default."""
        items = build_session(
            db_session, DEFAULT_USER_ID, now=NOW, seed=SEED,
        )
        assert len(items) == TARGET_PROBLEMS

    def test_custom_target(self, db_session, default_user):
        """Can override the target count."""
        items = build_session(
            db_session, DEFAULT_USER_ID, target=5, now=NOW, seed=SEED,
        )
        assert len(items) == 5

    def test_reviews_included_when_due(self, db_session, default_user):
        """Due reviews show up in the session as is_review=True."""
        # Create two reviews
        t = NOW - timedelta(days=2)
        update_review(db_session, DEFAULT_USER_ID, "Addition", 1, False, now=t)
        update_review(db_session, DEFAULT_USER_ID, "Subtraction", 2, False, now=t)
        db_session.commit()

        # Build session at NOW (reviews are overdue)
        items = build_session(
            db_session, DEFAULT_USER_ID, now=NOW, seed=SEED,
        )
        assert len(items) == TARGET_PROBLEMS

        review_items = [it for it in items if it.is_review]
        new_items = [it for it in items if not it.is_review]
        assert len(review_items) == 2
        assert len(new_items) == TARGET_PROBLEMS - 2

    def test_reviews_not_included_before_due(self, db_session, default_user):
        """Reviews that aren't due yet don't appear in the session."""
        # Create a review due tomorrow
        update_review(db_session, DEFAULT_USER_ID, "Addition", 1, False, now=NOW)
        db_session.commit()

        # Build session NOW (review isn't due until NOW + 1 day)
        items = build_session(
            db_session, DEFAULT_USER_ID, now=NOW, seed=SEED,
        )
        review_items = [it for it in items if it.is_review]
        assert len(review_items) == 0

    def test_all_slots_can_be_reviews(self, db_session, default_user):
        """If more reviews are due than target, session is all reviews."""
        t = NOW - timedelta(days=2)
        # Create 12 reviews (more than TARGET_PROBLEMS=10)
        from generators.registry import list_topics
        topics = list_topics()
        count = 0
        for topic in topics:
            for diff in range(1, 4):  # 5 topics × 3 diffs = 15
                update_review(
                    db_session, DEFAULT_USER_ID, topic, diff,
                    False, now=t,
                )
                count += 1
                if count >= 12:
                    break
            if count >= 12:
                break
        db_session.commit()

        items = build_session(
            db_session, DEFAULT_USER_ID, target=10, now=NOW, seed=SEED,
        )
        # Should cap at target
        assert len(items) == 10
        # All should be reviews
        assert all(it.is_review for it in items)

    def test_new_problems_spread_across_topics(self, db_session, default_user):
        """New problems cover multiple topics (round-robin)."""
        items = build_session(
            db_session, DEFAULT_USER_ID, target=10, now=NOW, seed=SEED,
        )
        topics_seen = {it.problem.topic for it in items}
        # With 5 registered topics and 10 slots, we should see all 5
        assert len(topics_seen) >= 3  # at least 3, likely all 5

    def test_problems_are_valid(self, db_session, default_user):
        """Every problem in the session has the expected fields."""
        items = build_session(
            db_session, DEFAULT_USER_ID, now=NOW, seed=SEED,
        )
        for item in items:
            p = item.problem
            assert p.topic
            assert p.prompt
            assert p.correct_answer
            assert isinstance(p.solution_steps, list)
            assert len(p.solution_steps) > 0
            assert 1 <= p.difficulty <= 5

    def test_deterministic_with_seed(self, db_session, default_user):
        """Same seed → same problems (reproducible sessions)."""
        items1 = build_session(
            db_session, DEFAULT_USER_ID, now=NOW, seed=SEED,
        )
        items2 = build_session(
            db_session, DEFAULT_USER_ID, now=NOW, seed=SEED,
        )
        prompts1 = [it.problem.prompt for it in items1]
        prompts2 = [it.problem.prompt for it in items2]
        assert prompts1 == prompts2

    def test_different_seed_different_problems(self, db_session, default_user):
        """Different seeds → (very likely) different problems."""
        items1 = build_session(
            db_session, DEFAULT_USER_ID, now=NOW, seed=1,
        )
        items2 = build_session(
            db_session, DEFAULT_USER_ID, now=NOW, seed=999,
        )
        prompts1 = [it.problem.prompt for it in items1]
        prompts2 = [it.problem.prompt for it in items2]
        # They could overlap by chance, but the full set shouldn't match.
        assert prompts1 != prompts2

