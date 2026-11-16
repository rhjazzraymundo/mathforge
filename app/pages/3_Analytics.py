"""Analytics page — charts and insights from your practice history.

Demonstrates the OLTP → OLAP pipeline:
  Postgres (attempts table) → pandas DataFrame → DuckDB SQL → Plotly charts

Requires the database to have attempt data.
"""

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

st.set_page_config(page_title="Analytics – MathForge", page_icon="📊", layout="wide")
st.title("📊 Analytics")


# ------------------------------------------------------------------
# Database connection (required)
# ------------------------------------------------------------------

def _init_db():
    try:
        from db.engine import SessionLocal
        from db.repositories import get_or_create_default_user
        from sqlalchemy import text

        session = SessionLocal()
        session.execute(text("SELECT 1"))
        user = get_or_create_default_user(session)
        return session, user.id
    except Exception:
        return None, None


if "analytics_db_initialized" not in st.session_state:
    _sess, _uid = _init_db()
    st.session_state.analytics_db_session = _sess
    st.session_state.analytics_db_user_id = _uid
    st.session_state.analytics_db_available = _sess is not None
    st.session_state.analytics_db_initialized = True

db_session = st.session_state.analytics_db_session
db_user_id = st.session_state.analytics_db_user_id
db_available = st.session_state.analytics_db_available

if not db_available:
    st.warning(
        "⚠️ Database not connected — analytics require practice data.\n\n"
        "Run `docker compose up -d db` and `alembic upgrade head`, then reload."
    )
    st.stop()


# ------------------------------------------------------------------
# Load data
# ------------------------------------------------------------------

from analytics.queries import (
    load_attempts,
    accuracy_by_topic,
    trend_over_time,
    weakest_areas,
    top_error_tags,
    summary_stats,
)

df = load_attempts(db_session, db_user_id)

if df.empty:
    st.info(
        "📝 No attempts recorded yet.\n\n"
        "Go to **Practice** or **Daily Session** and answer some problems, "
        "then come back here to see your stats!"
    )
    st.stop()


# ------------------------------------------------------------------
# Headline metrics
# ------------------------------------------------------------------

stats = summary_stats(df)

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Attempts", f"{stats['total_attempts']:,}")
col2.metric("Overall Accuracy", f"{stats['overall_accuracy']}%")
col3.metric("Topics Practised", stats["total_topics"])
col4.metric("Avg Time / Problem", f"{stats['avg_time_sec']}s")

st.divider()


# ------------------------------------------------------------------
# Charts
# ------------------------------------------------------------------

try:
    import plotly.express as px

    # ── 1. Accuracy by Topic ─────────────────────────────────────
    st.subheader("🎯 Accuracy by Topic")

    acc_df = accuracy_by_topic(df)
    if not acc_df.empty:
        fig = px.bar(
            acc_df, x="topic", y="accuracy_pct",
            text="accuracy_pct",
            color="accuracy_pct",
            color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
            labels={"accuracy_pct": "Accuracy %", "topic": "Topic"},
        )
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        fig.update_layout(
            yaxis_range=[0, 105], showlegend=False,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Not enough data yet.")

    # ── 2. Trend Over Time ───────────────────────────────────────
    st.subheader("📈 Accuracy Trend Over Time")

    trend_df = trend_over_time(df)
    if not trend_df.empty and len(trend_df) > 0:
        fig = px.line(
            trend_df, x="day", y="accuracy_pct",
            markers=True,
            labels={"accuracy_pct": "Accuracy %", "day": "Date"},
        )
        fig.update_layout(yaxis_range=[0, 105])
        # Add a subtle reference line at 80%
        fig.add_hline(
            y=80, line_dash="dash", line_color="gray",
            annotation_text="80% target",
            annotation_position="top right",
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Practice for a few days to see your trend.")

    # ── 3. Weakest Areas ─────────────────────────────────────────
    st.subheader("🔻 Weakest Areas")
    st.caption("Topic + difficulty combos with the lowest accuracy (min 3 attempts)")

    weak_df = weakest_areas(df)
    if not weak_df.empty:
        weak_df["label"] = weak_df["topic"] + " L" + weak_df["difficulty"].astype(str)
        fig = px.bar(
            weak_df, x="label", y="accuracy_pct",
            text="accuracy_pct",
            color="accuracy_pct",
            color_continuous_scale=["#ef4444", "#f59e0b", "#22c55e"],
            labels={"accuracy_pct": "Accuracy %", "label": "Topic + Level"},
        )
        fig.update_traces(texttemplate="%{text}%", textposition="outside")
        fig.update_layout(
            yaxis_range=[0, 105], showlegend=False,
            coloraxis_showscale=False,
        )
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Need at least 3 attempts per area to identify weak spots.")

    # ── 4. Top Error Tags ────────────────────────────────────────
    st.subheader("💡 Most Common Mistakes")

    err_df = top_error_tags(df)
    if not err_df.empty:
        # Make error tags readable
        err_df["label"] = (
            err_df["error_tag"]
            .str.replace("_", " ")
            .str.replace("-", " ")
            .str.title()
            + " (" + err_df["topic"] + ")"
        )
        fig = px.bar(
            err_df, x="count", y="label",
            orientation="h",
            color="topic",
            labels={"count": "Occurrences", "label": "Error Type"},
        )
        fig.update_layout(yaxis={"categoryorder": "total ascending"})
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("No error patterns detected yet — keep practising!")

except ImportError:
    # Fallback: use Streamlit's built-in charts if plotly isn't installed.
    st.warning("Install `plotly` for richer charts: `pip install plotly`")

    st.subheader("🎯 Accuracy by Topic")
    acc_df = accuracy_by_topic(df)
    if not acc_df.empty:
        st.bar_chart(acc_df.set_index("topic")["accuracy_pct"])

    st.subheader("📈 Accuracy Trend Over Time")
    trend_df = trend_over_time(df)
    if not trend_df.empty:
        st.line_chart(trend_df.set_index("day")["accuracy_pct"])


# ------------------------------------------------------------------
# Raw data explorer (collapsible)
# ------------------------------------------------------------------

with st.expander("🔍 Raw Attempt Data"):
    st.caption(f"Showing all {len(df)} attempts")
    st.dataframe(
        df.sort_values("created_at", ascending=False),
        use_container_width=True,
        hide_index=True,
    )
