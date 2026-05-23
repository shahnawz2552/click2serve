"""Owner login page."""
from __future__ import annotations

import streamlit as st

from core.auth import authenticate
from core.styles import inject_global_css

inject_global_css()

# Center the login card on a wide screen
left, mid, right = st.columns([1, 1.4, 1])

with mid:
    st.markdown(
        """
        <div style="text-align:center; margin-top:2rem; margin-bottom:1.2rem;">
            <div style="
                width: 60px; height: 60px;
                border-radius: 18px;
                background: linear-gradient(135deg, #7B68EE 0%, #FB3F8C 100%);
                display: inline-flex; align-items: center; justify-content: center;
                font-size: 1.8rem;
                box-shadow: 0 10px 26px rgba(123,104,238,0.32);
                margin-bottom: 0.8rem;
            ">🔐</div>
            <h2 style="margin: 0 0 0.3rem 0;">Owner Sign In</h2>
            <div style="color:#5C5F7C; font-size:0.95rem;">
                Shop staff &amp; owner access only.
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    if st.session_state.get("logged_in"):
        st.success(f"Already logged in as **{st.session_state.get('username')}**.")
        st.page_link("pages/dashboard.py", label="Go to Dashboard →",
                     use_container_width=True)
        st.stop()

    with st.container(border=True):
        with st.form("login_form"):
            username = st.text_input("Username", value="admin")
            password = st.text_input("Password", type="password",
                                     placeholder="default: click2serve123")
            remember = st.checkbox("Stay signed in for this browser session",
                                   value=True)
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
