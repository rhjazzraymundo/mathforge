"""Practice page — pick a topic and difficulty, solve problems, get feedback."""

import sys
from pathlib import Path

_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import random
import math
import streamlit as st
from generators.registry import list_topics, get_generator

st.set_page_config(page_title="Practice – MathForge", page_icon="📝")
st.title("📝 Practice")

# ------------------------------------------------------------------
# Sidebar controls
# ------------------------------------------------------------------
topic = st.selectbox("Topic", list_topics(), key="topic_select")
difficulty = st.slider("Difficulty", 1, 5, value=1, key="difficulty_slider")

# ------------------------------------------------------------------
# Session state — track current problem, answer status, counter
# ------------------------------------------------------------------
if "problem_counter" not in st.session_state:
    st.session_state.problem_counter = 0
if "prev_topic" not in st.session_state:
    st.session_state.prev_topic = topic
if "prev_difficulty" not in st.session_state:
    st.session_state.prev_difficulty = difficulty
if "answered" not in st.session_state:
    st.session_state.answered = False

# When the user changes topic or difficulty, reset for a new problem.
if topic != st.session_state.prev_topic or difficulty != st.session_state.prev_difficulty:
    st.session_state.prev_topic = topic
    st.session_state.prev_difficulty = difficulty
    st.session_state.problem_counter += 1
    st.session_state.answered = False

# ------------------------------------------------------------------
# Generate problem (deterministic for this counter)
# ------------------------------------------------------------------
rng = random.Random(st.session_state.problem_counter)
gen = get_generator(topic)
problem = gen(difficulty, rng)

st.markdown(f"### {problem.prompt}")

# ------------------------------------------------------------------
# Answer input & feedback
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

    if is_correct:
        st.success("✅ Correct! Nice work!")
    else:
        # Check for "forgot to simplify" — the student's fraction equals
        # the correct value but wasn't reduced (e.g. "4/6" vs "2/3").
        forgot_simplify = False
        if "/" in user_ans and problem.topic == "Fractions":
            try:
                parts = user_ans.split("/")
                u_num, u_den = int(parts[0]), int(parts[1])
                # Parse correct answer the same way
                if "/" in problem.correct_answer:
                    c_parts = problem.correct_answer.split("/")
                    c_num, c_den = int(c_parts[0]), int(c_parts[1])
                else:
                    c_num, c_den = int(problem.correct_answer), 1
                # Same value but not simplified?
                if u_num * c_den == c_num * u_den and math.gcd(abs(u_num), u_den) > 1:
                    forgot_simplify = True
            except (ValueError, IndexError, ZeroDivisionError):
                pass

        if forgot_simplify:
            st.warning(f"Almost! **{user_ans}** is correct but not fully simplified. "
                       f"The simplified answer is **{problem.correct_answer}**.")
        else:
            st.error(f"❌ Not quite. The correct answer is **{problem.correct_answer}**.")
            # Check for a known error pattern
            if user_ans in problem.common_wrong_answers:
                tag = problem.common_wrong_answers[user_ans]
                friendly = tag.replace("_", " ").replace("-", " ").title()
                st.info(f"💡 This looks like a **{friendly}** error.")

    # Worked solution
    with st.expander("📖 Worked Solution", expanded=not is_correct):
        for step in problem.solution_steps:
            st.text(step)

    # Next problem button
    if st.button("➡️ Next Problem"):
        st.session_state.problem_counter += 1
        st.session_state.answered = False
        st.rerun()

