"""Daily Session page — a timed ~10-problem session mixing reviews and new problems.

Flow:
  1. Click "Start Session" → session builder assembles problems.
  2. Work through each problem one at a time (progress bar + timer).
  3. After submitting, see feedback + worked solution, then Next.
  4. When all done, see a summary of results.

Requires the database — without it, use the Practice page instead.
"""

import sys
import time
import math
import random
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

st.set_page_config(page_title="Daily Session – MathForge", page_icon="🔥")
st.title("🔥 Daily Session")


# ------------------------------------------------------------------
# Database connection (required for sessions)
# ------------------------------------------------------------------

def _init_db():
    """Try to connect to Postgres and return (session, user_id)."""
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


if "daily_db_initialized" not in st.session_state:
    _sess, _uid = _init_db()
    st.session_state.daily_db_session = _sess
    st.session_state.daily_db_user_id = _uid
    st.session_state.daily_db_available = _sess is not None
    st.session_state.daily_db_initialized = True

db_session = st.session_state.daily_db_session
db_user_id = st.session_state.daily_db_user_id
db_available = st.session_state.daily_db_available

if not db_available:
    st.warning(
        "⚠️ Database not connected — daily sessions need the database to track "
        "reviews and mastery.\n\n"
        "Run `docker compose up -d db` and `alembic upgrade head`, then reload.\n\n"
        "In the meantime, use the **Practice** page for free practice."
    )
    st.stop()


# ------------------------------------------------------------------
# Session state defaults
# ------------------------------------------------------------------

_SESSION_DEFAULTS = {
    "session_active": False,
    "session_items": [],       # list of SessionItem
    "session_index": 0,        # which problem we're on
    "session_results": [],     # list of dicts with per-problem outcomes
    "session_start_time": 0.0,
    "problem_start_time": 0.0,
    "problem_answered": False,
    "problem_last_answer": "",
    "session_complete": False,
}
for key, default in _SESSION_DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default


# ------------------------------------------------------------------
# Helper: record an answer and update mastery + review queue
# ------------------------------------------------------------------

def _record_and_tag(problem, user_ans, is_correct, elapsed_ms):
    """Record attempt via mastery service; return (mastery_status, error_tag)."""
    from services.mastery import record_attempt

    error_tag = problem.common_wrong_answers.get(user_ans)
    status = record_attempt(
        session=db_session,
        user_id=db_user_id,
        topic=problem.topic,
        difficulty=problem.difficulty,
        is_correct=is_correct,
        user_answer=user_ans,
        correct_answer=problem.correct_answer,
        error_tag=error_tag,
        time_taken_ms=elapsed_ms,
    )
    return status, error_tag


# ------------------------------------------------------------------
# START screen
# ------------------------------------------------------------------

if not st.session_state.session_active and not st.session_state.session_complete:
    st.markdown(
        "Your daily session mixes **review problems** (topics you've missed "
        "before) with **new problems** at your current mastery level.\n\n"
        "**10 problems · ~10 minutes · let's go!**"
    )

    # Show how many reviews are due
    from db.repositories import get_due_reviews
    due = get_due_reviews(db_session, db_user_id)
    if due:
        st.info(f"📋 You have **{len(due)}** review item(s) due today.")
    else:
        st.success("✅ No reviews due — your session will be all new problems!")

    if st.button("🚀 Start Session", type="primary"):
        from services.session_builder import build_session

        items = build_session(db_session, db_user_id)
        st.session_state.session_items = items
        st.session_state.session_index = 0
        st.session_state.session_results = []
        st.session_state.session_active = True
        st.session_state.session_complete = False
        st.session_state.session_start_time = time.time()
        st.session_state.problem_start_time = time.time()
        st.session_state.problem_answered = False
        st.session_state.problem_last_answer = ""
        st.rerun()


# ------------------------------------------------------------------
# PROBLEM screen (active session)
# ------------------------------------------------------------------

elif st.session_state.session_active:
    items = st.session_state.session_items
    idx = st.session_state.session_index
    total = len(items)

    if idx >= total:
        # Shouldn't happen, but handle gracefully.
        st.session_state.session_active = False
        st.session_state.session_complete = True
        st.rerun()

    item = items[idx]
    problem = item.problem

    # ── Progress bar + timer ─────────────────────────────────────
    progress = (idx) / total
    st.progress(progress, text=f"Problem {idx + 1} of {total}")

    elapsed_total = time.time() - st.session_state.session_start_time
    mins, secs = divmod(int(elapsed_total), 60)

    col1, col2 = st.columns([1, 1])
    with col1:
        badge = "🔄 Review" if item.is_review else "🆕 New"
        st.caption(f"{badge} · {problem.topic} · Level {problem.difficulty}")
    with col2:
        st.caption(f"⏱️ {mins:02d}:{secs:02d} elapsed")

    # ── Problem prompt ───────────────────────────────────────────
    st.markdown(f"### {problem.prompt}")

    # ── Answer or feedback ───────────────────────────────────────
    if not st.session_state.problem_answered:
        with st.form("daily_answer_form", clear_on_submit=False):
            user_answer = st.text_input("Your answer:", key="daily_user_answer")
            submitted = st.form_submit_button("✅ Check Answer")

        if submitted and user_answer.strip():
            st.session_state.problem_answered = True
            st.session_state.problem_last_answer = user_answer.strip()
            st.rerun()
        elif submitted:
            st.warning("Type an answer first!")
    else:
        user_ans = st.session_state.problem_last_answer
        is_correct = user_ans == problem.correct_answer

        # Record attempt (once)
        result_key = f"result_recorded_{idx}"
        if result_key not in st.session_state:
            try:
                elapsed_ms = int(
                    (time.time() - st.session_state.problem_start_time) * 1000
                )
                status, error_tag = _record_and_tag(
                    problem, user_ans, is_correct, elapsed_ms,
                )
                st.session_state[result_key] = True
                st.session_state.session_results.append({
                    "topic": problem.topic,
                    "difficulty": problem.difficulty,
                    "is_review": item.is_review,
                    "is_correct": is_correct,
                    "error_tag": error_tag,
                    "promoted": status.promoted if status else False,
                    "user_answer": user_ans,
                    "correct_answer": problem.correct_answer,
                })
            except Exception as exc:
                st.warning(f"⚠️ Could not save attempt: {exc}")
                st.session_state[result_key] = True

        # Level-up celebration
        results_so_far = st.session_state.session_results
        if results_so_far and results_so_far[-1].get("promoted"):
            st.balloons()
            st.success(f"🎉 Level up in {problem.topic}!")

        # Feedback
        if is_correct:
            st.success("✅ Correct!")
        else:
            # Check for unsimplified fractions
            forgot_simplify = False
            if "/" in user_ans and problem.topic == "Fractions":
                try:
                    parts = user_ans.split("/")
                    u_num, u_den = int(parts[0]), int(parts[1])
                    if "/" in problem.correct_answer:
                        c_parts = problem.correct_answer.split("/")
                        c_num, c_den = int(c_parts[0]), int(c_parts[1])
                    else:
                        c_num, c_den = int(problem.correct_answer), 1
                    if u_num * c_den == c_num * u_den and math.gcd(abs(u_num), u_den) > 1:
                        forgot_simplify = True
                except (ValueError, IndexError, ZeroDivisionError):
                    pass

            if forgot_simplify:
                st.warning(
                    f"Almost! **{user_ans}** is correct but not simplified. "
                    f"Answer: **{problem.correct_answer}**."
                )
            else:
                st.error(
                    f"❌ Not quite. The answer is **{problem.correct_answer}**."
                )
                if user_ans in problem.common_wrong_answers:
                    tag = problem.common_wrong_answers[user_ans]
                    friendly = tag.replace("_", " ").replace("-", " ").title()
                    st.info(f"💡 This looks like a **{friendly}** error.")

        # Worked solution
        with st.expander("📖 Worked Solution", expanded=not is_correct):
            for step in problem.solution_steps:
                st.text(step)

        # Next / Finish
        is_last = idx + 1 >= total
        btn_label = "🏁 Finish Session" if is_last else "➡️ Next Problem"

        if st.button(btn_label):
            if is_last:
                st.session_state.session_active = False
                st.session_state.session_complete = True
            else:
                st.session_state.session_index += 1
                st.session_state.problem_answered = False
                st.session_state.problem_last_answer = ""
                st.session_state.problem_start_time = time.time()
            st.rerun()


# ------------------------------------------------------------------
# SUMMARY screen
# ------------------------------------------------------------------

elif st.session_state.session_complete:
    results = st.session_state.session_results
    total_time = time.time() - st.session_state.session_start_time
    mins, secs = divmod(int(total_time), 60)

    correct = sum(1 for r in results if r["is_correct"])
    total = len(results)
    reviews = sum(1 for r in results if r["is_review"])
    new = total - reviews
    promotions = sum(1 for r in results if r.get("promoted"))

    st.markdown("## 🏁 Session Complete!")
    st.markdown(f"**Time:** {mins}m {secs}s")

    # Score
    col1, col2, col3 = st.columns(3)
    col1.metric("Score", f"{correct}/{total}")
    col2.metric("Reviews", f"{reviews}")
    col3.metric("New", f"{new}")

    if promotions:
        st.success(f"🎉 You leveled up {promotions} time(s) this session!")

    if correct == total:
        st.success("💯 Perfect session!")
    elif correct >= total * 0.8:
        st.success("🌟 Great work!")
    elif correct >= total * 0.5:
        st.info("👍 Solid effort — keep practising!")
    else:
        st.info("💪 Keep at it — missed topics will come back for review.")

    # Per-problem breakdown
    st.markdown("### Problem-by-problem")
    for i, r in enumerate(results, 1):
        badge = "🔄" if r["is_review"] else "🆕"
        icon = "✅" if r["is_correct"] else "❌"
        tag_str = f"  ·  💡 {r['error_tag']}" if r.get("error_tag") else ""
        promo = "  ·  🎉 Level up!" if r.get("promoted") else ""
        st.text(
            f"{icon} {badge}  {r['topic']} L{r['difficulty']}  "
            f"Your answer: {r['user_answer']}  ·  "
            f"Correct: {r['correct_answer']}{tag_str}{promo}"
        )

    # Start another session
    if st.button("🔁 New Session", type="primary"):
        for key in _SESSION_DEFAULTS:
            st.session_state[key] = _SESSION_DEFAULTS[key]
        # Also clean up per-problem result keys
        keys_to_remove = [k for k in st.session_state if k.startswith("result_recorded_")]
        for k in keys_to_remove:
            del st.session_state[k]
        st.rerun()

