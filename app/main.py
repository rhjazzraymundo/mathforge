"""MathForge — main Streamlit entry point.

Run from the project root:
    streamlit run app/main.py
"""

import sys
from pathlib import Path

# Ensure project root is importable (generators/, services/, etc.)
_PROJECT_ROOT = str(Path(__file__).resolve().parent.parent)
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import streamlit as st

st.set_page_config(page_title="MathForge", page_icon="🔥", layout="centered")

st.title("🔥 MathForge")
st.subheader("Get better at math, one problem at a time")

st.markdown(
    """
    Welcome to **MathForge**!  Pick a mode from the sidebar:

    - 📝 **Practice** — choose a topic and difficulty, solve at your own pace
    - 📅 **Daily Session** — *(coming Phase 3)* timed 10-minute mixed session
    - 📊 **Analytics** — *(coming Phase 4)* charts of your progress
    """
)

st.divider()
st.caption("MathForge v0.1 · Phase 1 MVP")

