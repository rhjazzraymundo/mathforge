"""Tests for the spaced-repetition service.

Two groups:
  • Pure-logic tests — ``next_review_state`` (no DB).
  • DB integration tests — ``update_review`` via in-memory SQLite.
"""

import uuid
from datetime import datetime, timedelta, timezone

import pytest
from services.spaced_repetition import (
    INTERVALS,
    ReviewAction,
    next_review_state,
    update_review,
)
from db.repositories import DEFAULT_USER_ID, get_review, get_due_reviews


# ═══════════════════════════════════════════════════════════════════
# Pure-logic tests
# ═══════════════════════════════════════════════════════════════════


class TestNextReviewState:
    """Test the pure ``next_review_state`` function."""

    # --- Wrong answers always schedule a review at interval 1 ---

    def test_wrong_not_in_queue(self):
        """Wrong answer, not currently in queue → schedule at 1 day."""
        action = next_review_state(is_correct=False, current_interval=None)
        assert action.should_exist is True
        assert action.interval_days == 1
        assert action.graduated is False

    def test_wrong_resets_interval(self):
        """Wrong answer on a review at interval 3 → reset to 1."""
        action = next_review_state(is_correct=False, current_interval=3)
        assert action.should_exist is True
        assert action.interval_days == 1

    def test_wrong_resets_from_seven(self):
        """Wrong answer on a review at interval 7 → reset to 1."""
        action = next_review_state(is_correct=False, current_interval=7)
        assert action.should_exist is True
        assert action.interval_days == 1

    # --- Correct answers advance or graduate ---

    def test_correct_not_in_queue(self):
        """Correct answer, not in queue → no-op."""
        action = next_review_state(is_correct=True, current_interval=None)
        assert action.should_exist is False
        assert action.graduated is False

    def test_correct_advances_1_to_3(self):
        action = next_review_state(is_correct=True, current_interval=1)
        assert action.should_exist is True
        assert action.interval_days == 3

    def test_correct_advances_3_to_7(self):
        action = next_review_state(is_correct=True, current_interval=3)
        assert action.should_exist is True
        assert action.interval_days == 7

    def test_correct_graduates_from_7(self):
        """Correct at interval 7 → graduated (remove from queue)."""
        action = next_review_state(is_correct=True, current_interval=7)
        assert action.should_exist is False
        assert action.graduated is True

    # --- Edge case: unexpected interval value ---

    def test_correct_from_unexpected_interval(self):
        """If interval_days is 2 (not in INTERVALS), find next > 2 → 3."""
        action = next_review_state(is_correct=True, current_interval=2)
        assert action.should_exist is True
        assert action.interval_days == 3

    def test_correct_from_interval_above_max(self):
        """If interval_days > max in INTERVALS → graduate."""
        action = next_review_state(is_correct=True, current_interval=10)
        assert action.should_exist is False
        assert action.graduated is True


# ═══════════════════════════════════════════════════════════════════
# DB integration tests
# ═══════════════════════════════════════════════════════════════════


class TestUpdateReview:
    """Test ``update_review`` with an in-memory SQLite session."""

    NOW = datetime(2025, 6, 15, 12, 0, 0, tzinfo=timezone.utc)

    def test_wrong_creates_review(self, db_session, default_user):
        """Wrong answer creates a review entry due in 1 day."""
        action = update_review(
            db_session, DEFAULT_USER_ID,
            "Addition", 1, is_correct=False, now=self.NOW,
        )
        db_session.flush()

        assert action.should_exist is True
        review = get_review(db_session, DEFAULT_USER_ID, "Addition", 1)
        assert review is not None
        assert review.interval_days == 1
        # Compare without tzinfo — SQLite strips timezone info.
        expected = (self.NOW + timedelta(days=1)).replace(tzinfo=None)
        assert review.due_at.replace(tzinfo=None) == expected

    def test_wrong_resets_existing_review(self, db_session, default_user):
        """Wrong answer resets an existing review back to 1 day."""
        # Set up a review at interval 3
        update_review(
            db_session, DEFAULT_USER_ID,
            "Addition", 1, is_correct=False, now=self.NOW,
        )
        # Advance to 3
        update_review(
            db_session, DEFAULT_USER_ID,
            "Addition", 1, is_correct=True, now=self.NOW + timedelta(days=1),
        )
        review = get_review(db_session, DEFAULT_USER_ID, "Addition", 1)
        assert review.interval_days == 3

        # Now get it wrong — should reset to 1
        update_review(
            db_session, DEFAULT_USER_ID,
            "Addition", 1, is_correct=False, now=self.NOW + timedelta(days=4),
        )
        review = get_review(db_session, DEFAULT_USER_ID, "Addition", 1)
        assert review.interval_days == 1

    def test_correct_advances_review(self, db_session, default_user):
        """Correct answer on a review advances the interval."""
        # Create a review
        update_review(
            db_session, DEFAULT_USER_ID,
            "Addition", 1, is_correct=False, now=self.NOW,
        )
        # Answer correctly at day 1 → should advance to interval 3
        day1 = self.NOW + timedelta(days=1)
        action = update_review(
            db_session, DEFAULT_USER_ID,
            "Addition", 1, is_correct=True, now=day1,
        )
        assert action.interval_days == 3
        review = get_review(db_session, DEFAULT_USER_ID, "Addition", 1)
        assert review.interval_days == 3
        # Compare without tzinfo — SQLite strips timezone info.
        expected = (day1 + timedelta(days=3)).replace(tzinfo=None)
        assert review.due_at.replace(tzinfo=None) == expected

    def test_correct_graduates_review(self, db_session, default_user):
        """Correct answers through all intervals → graduated (removed)."""
        t = self.NOW

        # Wrong → creates at interval 1
        update_review(db_session, DEFAULT_USER_ID, "Addition", 1, False, now=t)

        # Correct → 1 → 3
        t += timedelta(days=1)
        update_review(db_session, DEFAULT_USER_ID, "Addition", 1, True, now=t)
        assert get_review(db_session, DEFAULT_USER_ID, "Addition", 1).interval_days == 3

        # Correct → 3 → 7
        t += timedelta(days=3)
        update_review(db_session, DEFAULT_USER_ID, "Addition", 1, True, now=t)
        assert get_review(db_session, DEFAULT_USER_ID, "Addition", 1).interval_days == 7

        # Correct → 7 → graduated (removed)
        t += timedelta(days=7)
        action = update_review(db_session, DEFAULT_USER_ID, "Addition", 1, True, now=t)
        assert action.graduated is True
        assert get_review(db_session, DEFAULT_USER_ID, "Addition", 1) is None

    def test_correct_no_review_is_noop(self, db_session, default_user):
        """Correct answer when nothing is in the queue → no row created."""
        action = update_review(
            db_session, DEFAULT_USER_ID,
            "Addition", 1, is_correct=True, now=self.NOW,
        )
        assert action.should_exist is False
        assert get_review(db_session, DEFAULT_USER_ID, "Addition", 1) is None

    def test_due_reviews_returns_only_due(self, db_session, default_user):
        """get_due_reviews only returns items whose due_at <= now."""
        t = self.NOW
        # Two wrong answers → two reviews due in 1 day
        update_review(db_session, DEFAULT_USER_ID, "Addition", 1, False, now=t)
        update_review(db_session, DEFAULT_USER_ID, "Subtraction", 2, False, now=t)
        db_session.flush()

        # Before they're due → nothing
        due = get_due_reviews(db_session, DEFAULT_USER_ID, as_of=t)
        assert len(due) == 0

        # At exactly due time → both show up
        due = get_due_reviews(db_session, DEFAULT_USER_ID, as_of=t + timedelta(days=1))
        assert len(due) == 2

    def test_multiple_topics_independent(self, db_session, default_user):
        """Reviews for different topics don't interfere with each other."""
        t = self.NOW
        update_review(db_session, DEFAULT_USER_ID, "Addition", 1, False, now=t)
        update_review(db_session, DEFAULT_USER_ID, "Multiplication", 3, False, now=t)

        # Advance Addition only
        t += timedelta(days=1)
        update_review(db_session, DEFAULT_USER_ID, "Addition", 1, True, now=t)

        add_rev = get_review(db_session, DEFAULT_USER_ID, "Addition", 1)
        mul_rev = get_review(db_session, DEFAULT_USER_ID, "Multiplication", 3)

        assert add_rev.interval_days == 3
        assert mul_rev.interval_days == 1  # unchanged