"""Owner login page."""
from __future__ import annotations

import streamlit as st

from core.auth import authenticate

st.title("🔐 Owner Login")
st.caption("Shop staff & owner access only.")

if st.session_state.get("logged_in"):
    st.success(f"Already logged in as **{st.session_state.get('username')}**.")
    st.page_link("pages/dashboard.py", label="Go to Dashboard →",
                 use_container_width=True)
    st.stop()

with st.form("login_form"):
    username = st.text_input("Username", value="admin")
    password = st.text_input("Password", type="password",
                             placeholder="default: click2serve123")
    remember = st.checkbox("Stay signed in for this browser session", value=True)
    submit = st.form_submit_button("Sign in", type="primary",
                                   use_container_width=True)

if submit:
    if authenticate(username, password):
        st.session_state["logged_in"] = True
        st.session_state["username"] = username.strip().lower()
        st.session_state["remember_login"] = remember
        st.success("Signed in. Redirecting…")
        st.rerun()
    else:
        st.error("Invalid username or password. Try again.")

with st.expander("First-time setup"):
    st.markdown(
        """
        **Default credentials**

        - **Username:** `admin`
        - **Password:** `click2serve123`

        After logging in, change the password in **Dashboard → Settings**.
        These defaults are only seeded on the very first run; subsequent
        deployments preserve any password you set.
        """
    )
