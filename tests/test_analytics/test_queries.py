"""Tests for analytics queries.

Strategy: build a synthetic DataFrame of attempts (no DB needed!)
and verify that DuckDB queries return the expected aggregations.
This is fast and deterministic.
"""

from datetime import datetime, timezone

import pandas as pd
import pytest

from analytics.queries import (
    accuracy_by_topic,
    trend_over_time,
    weakest_areas,
    top_error_tags,
    summary_stats,
)


# ---------------------------------------------------------------------------
# Fixtures — synthetic attempt data
# ---------------------------------------------------------------------------

def _make_df(rows: list[dict]) -> pd.DataFrame:
    """Build a DataFrame matching the shape load_attempts() returns."""
    columns = [
        "topic", "difficulty", "is_correct",
        "error_tag", "time_taken_ms", "created_at",
    ]
    if not rows:
        return pd.DataFrame(columns=columns)

    defaults = {
        "topic": "Addition",
        "difficulty": 1,
        "is_correct": True,
        "error_tag": None,
        "time_taken_ms": 5000,
        "created_at": datetime(2025, 6, 15, 12, 0, tzinfo=timezone.utc),
    }
    full_rows = [{**defaults, **r} for r in rows]
    df = pd.DataFrame(full_rows)
    df["created_at"] = pd.to_datetime(df["created_at"])
    return df


@pytest.fixture
def sample_df() -> pd.DataFrame:
    """A realistic-ish dataset with multiple topics, days, and errors."""
    rows = []
    # Day 1: 10 Addition attempts (8 correct, 2 wrong)
    for i in range(8):
        rows.append({
            "topic": "Addition", "difficulty": 1, "is_correct": True,
            "created_at": datetime(2025, 6, 15, 10, i),
        })
    rows.append({
        "topic": "Addition", "difficulty": 1, "is_correct": False,
        "error_tag": "forgot_to_carry",
        "created_at": datetime(2025, 6, 15, 10, 8),
    })
    rows.append({
        "topic": "Addition", "difficulty": 1, "is_correct": False,
        "error_tag": "forgot_to_carry",
        "created_at": datetime(2025, 6, 15, 10, 9),
    })

    # Day 1: 5 Subtraction attempts (3 correct, 2 wrong)
    for i in range(3):
        rows.append({
            "topic": "Subtraction", "difficulty": 2, "is_correct": True,
            "created_at": datetime(2025, 6, 15, 11, i),
        })
    rows.append({
        "topic": "Subtraction", "difficulty": 2, "is_correct": False,
        "error_tag": "sign_error",
        "created_at": datetime(2025, 6, 15, 11, 3),
    })
    rows.append({
        "topic": "Subtraction", "difficulty": 2, "is_correct": False,
        "error_tag": "no_borrow_sub",
        "created_at": datetime(2025, 6, 15, 11, 4),
    })

    # Day 2: 5 Addition (all correct) → improvement!
    for i in range(5):
        rows.append({
            "topic": "Addition", "difficulty": 2, "is_correct": True,
            "created_at": datetime(2025, 6, 16, 10, i),
        })

    # Day 2: 3 Fractions (1 correct, 2 wrong)
    rows.append({
        "topic": "Fractions", "difficulty": 1, "is_correct": True,
        "created_at": datetime(2025, 6, 16, 11, 0),
    })
    rows.append({
        "topic": "Fractions", "difficulty": 1, "is_correct": False,
        "error_tag": "wrong_denominator",
        "created_at": datetime(2025, 6, 16, 11, 1),
    })
    rows.append({
        "topic": "Fractions", "difficulty": 1, "is_correct": False,
        "error_tag": "wrong_denominator",
        "created_at": datetime(2025, 6, 16, 11, 2),
    })

    return _make_df(rows)


@pytest.fixture
def empty_df() -> pd.DataFrame:
    return _make_df([])


# ═══════════════════════════════════════════════════════════════════
# Tests
# ═══════════════════════════════════════════════════════════════════


class TestAccuracyByTopic:

    def test_returns_all_topics(self, sample_df):
        result = accuracy_by_topic(sample_df)
        topics = set(result["topic"])
        assert topics == {"Addition", "Subtraction", "Fractions"}

    def test_accuracy_values(self, sample_df):
        result = accuracy_by_topic(sample_df)
        result = result.set_index("topic")
        # Addition: 13 correct / 15 total = 86.7%
        assert result.loc["Addition", "accuracy_pct"] == pytest.approx(86.7, abs=0.1)
        # Subtraction: 3/5 = 60%
        assert result.loc["Subtraction", "accuracy_pct"] == pytest.approx(60.0, abs=0.1)
        # Fractions: 1/3 = 33.3%
        assert result.loc["Fractions", "accuracy_pct"] == pytest.approx(33.3, abs=0.1)

    def test_sorted_ascending(self, sample_df):
        result = accuracy_by_topic(sample_df)
        pcts = list(result["accuracy_pct"])
        assert pcts == sorted(pcts)

    def test_empty_df(self, empty_df):
        result = accuracy_by_topic(empty_df)
        assert result.empty


class TestTrendOverTime:

    def test_returns_two_days(self, sample_df):
        result = trend_over_time(sample_df)
        assert len(result) == 2

    def test_day_order(self, sample_df):
        result = trend_over_time(sample_df)
        days = list(result["day"])
        assert days == sorted(days)

    def test_day1_accuracy(self, sample_df):
        result = trend_over_time(sample_df)
        day1 = result.iloc[0]
        # Day 1: 11 correct / 15 total = 73.3%
        assert day1["total"] == 15
        assert day1["correct"] == 11
        assert day1["accuracy_pct"] == pytest.approx(73.3, abs=0.1)

    def test_day2_accuracy(self, sample_df):
        result = trend_over_time(sample_df)
        day2 = result.iloc[1]
        # Day 2: 6 correct / 8 total = 75%
        assert day2["total"] == 8
        assert day2["correct"] == 6
        assert day2["accuracy_pct"] == pytest.approx(75.0, abs=0.1)

    def test_empty_df(self, empty_df):
        result = trend_over_time(empty_df)
        assert result.empty


class TestWeakestAreas:

    def test_returns_weakest_first(self, sample_df):
        result = weakest_areas(sample_df)
        if len(result) > 1:
            pcts = list(result["accuracy_pct"])
            assert pcts == sorted(pcts)

    def test_minimum_three_attempts(self, sample_df):
        result = weakest_areas(sample_df)
        # Every row should have at least 3 attempts
        assert all(result["total"] >= 3)

    def test_fractions_is_weakest(self, sample_df):
        result = weakest_areas(sample_df)
        if not result.empty:
            # Fractions L1: 1/3 = 33.3% — should be the weakest
            assert result.iloc[0]["topic"] == "Fractions"

    def test_limit_works(self, sample_df):
        result = weakest_areas(sample_df, limit=1)
        assert len(result) <= 1

    def test_empty_df(self, empty_df):
        result = weakest_areas(empty_df)
        assert result.empty


class TestTopErrorTags:

    def test_returns_error_tags(self, sample_df):
        result = top_error_tags(sample_df)
        assert not result.empty
        assert "error_tag" in result.columns

    def test_most_common_first(self, sample_df):
        result = top_error_tags(sample_df)
        counts = list(result["count"])
        assert counts == sorted(counts, reverse=True)

    def test_forgot_to_carry_most_common(self, sample_df):
        result = top_error_tags(sample_df)
        # forgot_to_carry appears 2 times, same as wrong_denominator
        top_tags = set(result[result["count"] == result["count"].max()]["error_tag"])
        assert "forgot_to_carry" in top_tags or "wrong_denominator" in top_tags

    def test_null_tags_excluded(self, sample_df):
        result = top_error_tags(sample_df)
        assert result["error_tag"].notna().all()

    def test_limit_works(self, sample_df):
        result = top_error_tags(sample_df, limit=2)
        assert len(result) <= 2

    def test_empty_df(self, empty_df):
        result = top_error_tags(empty_df)
        assert result.empty


class TestSummaryStats:

    def test_total_attempts(self, sample_df):
        stats = summary_stats(sample_df)
        assert stats["total_attempts"] == 23

    def test_overall_accuracy(self, sample_df):
        stats = summary_stats(sample_df)
        # 17 correct / 23 total = 73.9%
        assert stats["overall_accuracy"] == pytest.approx(73.9, abs=0.1)

    def test_total_topics(self, sample_df):
        stats = summary_stats(sample_df)
        assert stats["total_topics"] == 3

    def test_avg_time(self, sample_df):
        stats = summary_stats(sample_df)
        # All rows default to 5000ms = 5.0s
        assert stats["avg_time_sec"] == pytest.approx(5.0, abs=0.1)

    def test_empty_df(self, empty_df):
        stats = summary_stats(empty_df)
        assert stats["total_attempts"] == 0
        assert stats["overall_accuracy"] == 0.0
