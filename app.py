"""Click2Serve — main entry point.

Uses st.navigation to dynamically route between Customer pages and Owner
(admin) pages based on session state. The owner sees admin pages only after
signing in; customers never see them.
"""
from __future__ import annotations

import streamlit as st

from core.db import init_db
from core.styles import inject_global_css

# ── Bootstrap database on first request ─────────────────────────────────────
init_db()

# ── Page config (only the entry point sets this) ────────────────────────────
st.set_page_config(
    page_title="Click2Serve — Digital Service Hub",
    page_icon="🛎️",
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": "Click2Serve — Your one-click digital service hub.",
    },
)

# ── Apply the global stylesheet to every page ───────────────────────────────
inject_global_css()

# ── Sidebar branding (shown on every page) ──────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="padding: 0.4rem 0 1.6rem 0; border-bottom: 1px solid #1F2620; margin-bottom: 1rem;">
            <div style="
                display: inline-block;
                width: 8px; height: 8px;
                background: #C7F284;
                border-radius: 50%;
                margin-right: 0.5rem;
                vertical-align: middle;
            "></div>
            <span style="
                font-size: 1.05rem; font-weight: 800;
                letter-spacing: -0.02em; color: #0E120F;
                vertical-align: middle;
            ">click2serve</span>
            <div style="
                font-size: 0.7rem; color: #5A6157;
                font-weight: 500; text-transform: uppercase;
                letter-spacing: 0.14em; margin-top: 0.5rem;
            ">Digital service hub</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Dynamic navigation based on auth state ─────────────────────────────────
def build_nav() -> dict[str, list[st.Page]]:
    customer_pages = [
        st.Page("pages/home.py", title="Home",
                icon=":material/home:", default=True),
        st.Page("pages/book.py", title="Book a service",
                icon=":material/edit_note:"),
        st.Page("pages/pay.py", title="Pay online",
                icon=":material/payments:"),
        st.Page("pages/track.py", title="Track booking",
                icon=":material/search:"),
    ]

    if st.session_state.get("logged_in"):
        owner_pages = [
            st.Page("pages/dashboard.py", title="Dashboard",
                    icon=":material/dashboard:"),
            st.Page("pages/bookings.py", title="Bookings",
                    icon=":material/folder_open:"),
            st.Page("pages/revenue.py", title="Revenue",
                    icon=":material/savings:"),
            st.Page("pages/settings.py", title="Settings",
                    icon=":material/tune:"),
            st.Page("pages/logout.py", title="Sign out",
                    icon=":material/logout:"),
        ]
    else:
        owner_pages = [
            st.Page("pages/login.py", title="Owner login",
                    icon=":material/lock:"),
        ]

    return {
        "Customer": customer_pages,
        "Owner": owner_pages,
    }


nav = st.navigation(build_nav())
nav.run()
