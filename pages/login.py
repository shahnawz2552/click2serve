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
        <div style="text-align:center; margin-top:2rem; margin-bottom:1.4rem;">
            <div style="
                font-size:0.74rem; font-weight:600;
                color:#0E120F; text-transform:uppercase;
                letter-spacing:0.16em; margin-bottom:0.8rem;
                display: inline-flex; align-items: center; gap: 0.55rem;
            "><span style="width:28px; height:1px; background:#0E120F;"></span>Owner access</div>
            <h2 style="margin:0 0 0.4rem 0; font-size:2rem; font-weight:900; letter-spacing:-0.035em;">
                Sign in to your dashboard.
            </h2>
            <div style="color:#5A6157; font-size:1rem;">
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
