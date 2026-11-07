"""Tests for the mastery service.

Split into two sections:
  1. TestCheckPromotion — pure function, no database needed.
  2. TestRecordAttempt  — integration tests using an in-memory SQLite database.
"""

import pytest
from services.mastery import (
    check_promotion,
    record_attempt,
    MasteryStatus,
    REQUIRED_CORRECT,
    REQUIRED_TOTAL,
)


# ===================================================================
# 1. Pure promotion logic
# ===================================================================

class TestCheckPromotion:
    """check_promotion is a pure function: (state, input) → new state."""

    def test_ten_correct_promotes(self):
        level, results, promoted = check_promotion(1, [True] * 9, True, at_difficulty=1)
        assert promoted
        assert level == 2
        assert results == []

    def test_eight_of_ten_promotes(self):
        # 7 correct + 2 wrong so far (9 attempts), then one more correct
        prior = [True, True, False, True, True, True, True, False, True]
        level, results, promoted = check_promotion(1, prior, True, at_difficulty=1)
        assert promoted  # 8/10 correct
        assert level == 2

    def test_seven_of_ten_does_not_promote(self):
        prior = [True, True, False, True, True, True, False, False, True]
        level, results, promoted = check_promotion(1, prior, True, at_difficulty=1)
        assert not promoted  # only 7/10
        assert level == 1
        assert len(results) == 10

    def test_needs_ten_attempts_minimum(self):
        """Even 8/8 correct shouldn't promote — need 10 total attempts."""
        level, results, promoted = check_promotion(1, [True] * 7, True, at_difficulty=1)
        assert not promoted
        assert level == 1
        assert len(results) == 8

    def test_wrong_difficulty_ignored(self):
        """Answers at a difficulty != current level don't affect mastery."""
        prior = [True] * 9
        level, results, promoted = check_promotion(1, prior, True, at_difficulty=3)
        assert not promoted
        assert level == 1
        assert results is prior  # unchanged reference

    def test_promotion_resets_results(self):
        level, results, promoted = check_promotion(1, [True] * 9, True, at_difficulty=1)
        assert results == []

    def test_results_capped_at_ten(self):
        prior = [True] * 5 + [False] * 5  # 10 items
        level, results, promoted = check_promotion(1, prior, False, at_difficulty=1)
        assert len(results) == 10
        # Oldest True dropped, newest False added
        expected = [True] * 4 + [False] * 5 + [False]
        assert results == expected

    def test_multi_level_progression(self):
        """Can go from level 1 → 2 → 3 with enough correct answers."""
        # Level 1 → 2
        results: list[bool] = []
        for _ in range(10):
            level, results, promoted = check_promotion(1, results, True, at_difficulty=1)
        assert promoted and level == 2 and results == []

        # Level 2 → 3
        for _ in range(10):
            level, results, promoted = check_promotion(level, results, True, at_difficulty=level)
        assert promoted and level == 3

    def test_wrong_answer_at_current_level_tracked(self):
        level, results, promoted = check_promotion(1, [], False, at_difficulty=1)
        assert results == [False]
        assert not promoted


# ===================================================================
# 2. Integration tests (in-memory SQLite)
# ===================================================================

class TestRecordAttempt:
    def test_attempt_saved(self, db_session, default_user):
        from db.models import Attempt

        record_attempt(
            db_session, default_user.id, "Addition", 1, True, "5", "5",
        )
        attempts = db_session.query(Attempt).all()
        assert len(attempts) == 1
        assert attempts[0].topic == "Addition"
        assert attempts[0].is_correct is True

    def test_mastery_auto_created(self, db_session, default_user):
        from db.models import Mastery

        record_attempt(
            db_session, default_user.id, "Addition", 1, True, "5", "5",
        )
        mastery = db_session.get(Mastery, (default_user.id, "Addition"))
        assert mastery is not None
        assert mastery.current_level == 1

    def test_full_promotion_flow(self, db_session, default_user):
        """10 correct answers at level 1 → promote to level 2."""
        status = None
        for _ in range(10):
            status = record_attempt(
                db_session, default_user.id, "Addition", 1, True, "5", "5",
            )
        assert status is not None
        assert status.promoted
        assert status.current_level == 2
        assert status.recent_results == []

    def test_wrong_difficulty_no_mastery_change(self, db_session, default_user):
        """Answering at difficulty != current_level logs the attempt but
        doesn't affect mastery."""
        from db.models import Attempt

        status = record_attempt(
            db_session, default_user.id, "Addition", 3, True, "5", "5",
        )
        assert not status.promoted
        assert status.current_level == 1
        assert status.recent_total == 0
        # But the attempt IS saved
        assert db_session.query(Attempt).count() == 1

    def test_error_tag_saved(self, db_session, default_user):
        from db.models import Attempt

        record_attempt(
            db_session, default_user.id, "Addition", 1, False,
            "72", "82", error_tag="forgot_to_carry",
        )
        attempt = db_session.query(Attempt).first()
        assert attempt.error_tag == "forgot_to_carry"

    def test_time_taken_saved(self, db_session, default_user):
        from db.models import Attempt

        record_attempt(
            db_session, default_user.id, "Addition", 1, True,
            "5", "5", time_taken_ms=4200,
        )
        attempt = db_session.query(Attempt).first()
        assert attempt.time_taken_ms == 4200

    def test_mastery_status_properties(self):
        ms = MasteryStatus("Addition", 2, [True, True, False])
        assert ms.recent_correct == 2
        assert ms.recent_total == 3
        assert not ms.promoted

