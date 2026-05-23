"""Owner logout — clears session state."""
from __future__ import annotations

import streamlit as st

for key in ("logged_in", "username", "remember_login"):
    st.session_state.pop(key, None)

st.success("Signed out.")
st.page_link("pages/home.py", label="← Back to home", use_container_width=True)
