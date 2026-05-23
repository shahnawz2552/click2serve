"""Owner logout — clears session state."""
from __future__ import annotations

import streamlit as st

from core.styles import inject_global_css, section_header

inject_global_css()

for key in ("logged_in", "username", "remember_login"):
    st.session_state.pop(key, None)

section_header(
    eyebrow="Signed out",
    title="See you next time.",
    subtitle="Your session has been cleared from this browser.",
)

st.page_link("pages/home.py", label="← Back to home",
             use_container_width=True)
