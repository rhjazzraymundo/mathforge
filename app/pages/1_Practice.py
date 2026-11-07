"""Practice page — pick a topic and difficulty, solve problems, get feedback.

Phase 2 additions:
  • Attempts are logged to Postgres (when the DB is available).
  • Mastery level + progress bar shown in the sidebar.
  • Level-up celebration (balloons!).
  • Answer time is tracked.
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
from generators.registry import list_topics, get_generator

st.set_page_config(page_title="Practice – MathForge", page_icon="📝")
st.title("📝 Practice")


# ------------------------------------------------------------------
# Database connection (gracefully optional)
# ------------------------------------------------------------------

def _init_db():
    """Try to connect to Postgres and return (session, user_id).
    Returns (None, None) if the DB is unavailable."""
    try:
        from db.engine import SessionLocal
        from db.repositories import get_or_create_default_user
        from sqlalchemy import text

        session = SessionLocal()
        session.execute(text("SELECT 1"))  # fast connectivity check
        user = get_or_create_default_user(session)
        return session, user.id
    except Exception:
        return None, None


if "db_initialized" not in st.session_state:
    _sess, _uid = _init_db()
    st.session_state.db_session = _sess
    st.session_state.db_user_id = _uid
    st.session_state.db_available = _sess is not None
    st.session_state.db_initialized = True

db_session = st.session_state.db_session
db_user_id = st.session_state.db_user_id
db_available = st.session_state.db_available

if not db_available:
    st.info(
        "💡 Database not connected — attempts won't be saved.  \n"
        "Run `docker compose up -d db` and `alembic upgrade head`, then reload."
    )


# ------------------------------------------------------------------
# Topic & difficulty controls
# ------------------------------------------------------------------

topic = st.selectbox("Topic", list_topics(), key="topic_select")
difficulty = st.slider("Difficulty", 1, 5, value=1, key="difficulty_slider")


# ------------------------------------------------------------------
# Session state
# ------------------------------------------------------------------

_DEFAULTS = {
    "problem_counter": 0,
    "prev_topic": None,
    "prev_difficulty": None,
    "answered": False,
    "attempt_recorded": False,
    "last_answer": "",
    "problem_start_time": time.time(),
    "mastery_status": None,
}
for key, default in _DEFAULTS.items():
    if key not in st.session_state:
        st.session_state[key] = default

# Detect topic / difficulty change → new problem.
if topic != st.session_state.prev_topic or difficulty != st.session_state.prev_difficulty:
    st.session_state.prev_topic = topic
    st.session_state.prev_difficulty = difficulty
    st.session_state.problem_counter += 1
    st.session_state.answered = False
    st.session_state.attempt_recorded = False
    st.session_state.problem_start_time = time.time()
    st.session_state.mastery_status = None


# ------------------------------------------------------------------
# Generate problem (deterministic per counter)
# ------------------------------------------------------------------

rng = random.Random(st.session_state.problem_counter)
gen = get_generator(topic)
problem = gen(difficulty, rng)

st.markdown(f"### {problem.prompt}")


# ------------------------------------------------------------------
# Answer form  ──or──  feedback
# ------------------------------------------------------------------

if not st.session_state.answered:
    with st.form("answer_form", clear_on_submit=False):
        user_answer = st.text_input("Your answer:", key="user_answer_input")
        submitted = st.form_submit_button("✅ Check Answer")

    if submitted and user_answer.strip():
        st.session_state.answered = True
        st.session_state.last_answer = user_answer.strip()
        st.rerun()
    elif submitted:
        st.warning("Type an answer first!")

else:
    user_ans = st.session_state.last_answer
    is_correct = user_ans == problem.correct_answer

    # ── Record attempt (once per answer) ─────────────────────────
    if not st.session_state.attempt_recorded:
        if db_available:
            try:
                from services.mastery import record_attempt

                elapsed_ms = int((time.time() - st.session_state.problem_start_time) * 1000)
                error_tag = problem.common_wrong_answers.get(user_ans)

                status = record_attempt(
                    session=db_session,
                    user_id=db_user_id,
                    topic=topic,
                    difficulty=difficulty,
                    is_correct=is_correct,
                    user_answer=user_ans,
                    correct_answer=problem.correct_answer,
                    error_tag=error_tag,
                    time_taken_ms=elapsed_ms,
                )
                st.session_state.mastery_status = status
            except Exception as exc:
                st.warning(f"⚠️ Could not save attempt: {exc}")
        st.session_state.attempt_recorded = True

    # ── Level-up celebration ─────────────────────────────────────
    ms = st.session_state.mastery_status
    if ms and ms.promoted:
        st.balloons()
        st.success(
            f"🎉 **Level up!** You're now at **Level {ms.current_level}** in {topic}!"
        )

    # ── Correctness feedback ─────────────────────────────────────
    if is_correct:
        st.success("✅ Correct! Nice work!")
    else:
        # Check for "forgot to simplify" (fraction is correct but unreduced)
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
                f"Almost! **{user_ans}** is correct but not fully simplified. "
                f"The simplified answer is **{problem.correct_answer}**."
            )
        else:
            st.error(f"❌ Not quite. The correct answer is **{problem.correct_answer}**.")
            if user_ans in problem.common_wrong_answers:
                tag = problem.common_wrong_answers[user_ans]
                friendly = tag.replace("_", " ").replace("-", " ").title()
                st.info(f"💡 This looks like a **{friendly}** error.")

    # ── Worked solution ──────────────────────────────────────────
    with st.expander("📖 Worked Solution", expanded=not is_correct):
        for step in problem.solution_steps:
            st.text(step)

    # ── Next problem ─────────────────────────────────────────────
    if st.button("➡️ Next Problem"):
        st.session_state.problem_counter += 1
        st.session_state.answered = False
        st.session_state.attempt_recorded = False
        st.session_state.problem_start_time = time.time()
        st.session_state.mastery_status = None
        st.rerun()


# ------------------------------------------------------------------
# Sidebar: mastery progress (rendered last so it reflects updates)
# ------------------------------------------------------------------

if db_available:
    try:
        from db.repositories import get_or_create_mastery

        m = get_or_create_mastery(db_session, db_user_id, topic)
        recent = list(m.recent_results) if m.recent_results else []
        correct_count = sum(recent)

        with st.sidebar:
            st.subheader(f"📊 {topic}")
            st.metric("Mastery Level", m.current_level)
            st.progress(
                min(correct_count / 10, 1.0),
                text=f"{correct_count}/10 correct at Level {m.current_level}",
            )
    except Exception:
        pass
