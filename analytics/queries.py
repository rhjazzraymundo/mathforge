"""Analytical queries powered by DuckDB.

Architecture
------------
OLTP (Postgres)  →  pandas DataFrame  →  DuckDB SQL  →  chart-ready results

**Why two databases?**
Postgres is optimised for OLTP — fast single-row inserts and lookups.
DuckDB is optimised for OLAP — fast aggregations over millions of rows.
By loading attempts into a DataFrame first, DuckDB can crunch analytics
without touching the production database.

Every public function here returns a pandas DataFrame that a Streamlit
chart can consume directly.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import duckdb
import pandas as pd
from sqlalchemy import select
from sqlalchemy.orm import Session

from db.models import Attempt


# ---------------------------------------------------------------------------
# Extract: Postgres → pandas
# ---------------------------------------------------------------------------

def load_attempts(db_session: Session, user_id: uuid.UUID) -> pd.DataFrame:
    """Pull all attempts for a user into a pandas DataFrame.

    This is the "Extract" step of the mini-ETL pipeline.
    In a production system you'd export to Parquet and query from there;
    for our scale a simple SELECT is fine.
    """
    stmt = (
        select(
            Attempt.topic,
            Attempt.difficulty,
            Attempt.is_correct,
            Attempt.error_tag,
            Attempt.time_taken_ms,
            Attempt.created_at,
        )
        .where(Attempt.user_id == user_id)
        .order_by(Attempt.created_at)
    )
    rows = db_session.execute(stmt).all()

    if not rows:
        return pd.DataFrame(columns=[
            "topic", "difficulty", "is_correct",
            "error_tag", "time_taken_ms", "created_at",
        ])

    df = pd.DataFrame(rows, columns=[
        "topic", "difficulty", "is_correct",
        "error_tag", "time_taken_ms", "created_at",
    ])
    # Ensure created_at is a proper datetime (SQLite may return strings).
    df["created_at"] = pd.to_datetime(df["created_at"])
    return df


# ---------------------------------------------------------------------------
# Analyse: DuckDB queries on the DataFrame
# ---------------------------------------------------------------------------

def accuracy_by_topic(df: pd.DataFrame) -> pd.DataFrame:
    """Bar-chart data: overall accuracy (%) per topic.

    Returns columns: topic, total, correct, accuracy_pct
    """
    if df.empty:
        return pd.DataFrame(columns=["topic", "total", "correct", "accuracy_pct"])

    return duckdb.sql("""
        SELECT
            topic,
            COUNT(*)                              AS total,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS correct,
            ROUND(100.0 * SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)
                  / COUNT(*), 1)                  AS accuracy_pct
        FROM df
        GROUP BY topic
        ORDER BY accuracy_pct ASC
    """).df()


def trend_over_time(df: pd.DataFrame) -> pd.DataFrame:
    """Line-chart data: daily accuracy trend.

    Returns columns: day, total, correct, accuracy_pct
    """
    if df.empty:
        return pd.DataFrame(columns=["day", "total", "correct", "accuracy_pct"])

    return duckdb.sql("""
        SELECT
            CAST(created_at AS DATE)              AS day,
            COUNT(*)                              AS total,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS correct,
            ROUND(100.0 * SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)
                  / COUNT(*), 1)                  AS accuracy_pct
        FROM df
        GROUP BY day
        ORDER BY day
    """).df()


def weakest_areas(df: pd.DataFrame, limit: int = 5) -> pd.DataFrame:
    """Table data: topic + difficulty combos with the lowest accuracy.

    Only includes combos with at least 3 attempts so one bad answer
    doesn't dominate.

    Returns columns: topic, difficulty, total, correct, accuracy_pct
    """
    if df.empty:
        return pd.DataFrame(columns=[
            "topic", "difficulty", "total", "correct", "accuracy_pct",
        ])

    return duckdb.sql(f"""
        SELECT
            topic,
            difficulty,
            COUNT(*)                              AS total,
            SUM(CASE WHEN is_correct THEN 1 ELSE 0 END) AS correct,
            ROUND(100.0 * SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)
                  / COUNT(*), 1)                  AS accuracy_pct
        FROM df
        GROUP BY topic, difficulty
        HAVING COUNT(*) >= 3
        ORDER BY accuracy_pct ASC
        LIMIT {int(limit)}
    """).df()


def top_error_tags(df: pd.DataFrame, limit: int = 10) -> pd.DataFrame:
    """Bar-chart data: most frequent error tags.

    Filters out NULL error_tags (correct answers / unmatched wrong answers).

    Returns columns: error_tag, topic, count
    """
    if df.empty:
        return pd.DataFrame(columns=["error_tag", "topic", "count"])

    return duckdb.sql(f"""
        SELECT
            error_tag,
            topic,
            COUNT(*) AS count
        FROM df
        WHERE error_tag IS NOT NULL
        GROUP BY error_tag, topic
        ORDER BY count DESC
        LIMIT {int(limit)}
    """).df()


def summary_stats(df: pd.DataFrame) -> dict:
    """Quick headline numbers for the dashboard.

    Returns a dict with: total_attempts, overall_accuracy, total_topics,
    avg_time_sec, streak_today.
    """
    if df.empty:
        return {
            "total_attempts": 0,
            "overall_accuracy": 0.0,
            "total_topics": 0,
            "avg_time_sec": 0.0,
            "attempts_today": 0,
        }

    stats = duckdb.sql("""
        SELECT
            COUNT(*)                               AS total_attempts,
            ROUND(100.0 * SUM(CASE WHEN is_correct THEN 1 ELSE 0 END)
                  / COUNT(*), 1)                   AS overall_accuracy,
            COUNT(DISTINCT topic)                  AS total_topics,
            ROUND(AVG(time_taken_ms) / 1000.0, 1)  AS avg_time_sec,
            SUM(CASE WHEN CAST(created_at AS DATE) = CURRENT_DATE
                     THEN 1 ELSE 0 END)            AS attempts_today
        FROM df
    """).df()

    return stats.iloc[0].to_dict()
