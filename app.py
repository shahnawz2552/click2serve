"""Click2Serve — main entry point.

Uses st.navigation to dynamically route between Customer pages and Owner
(admin) pages based on session state. The owner sees admin pages only after
signing in; customers never see them.
"""
from __future__ import annotations

import streamlit as st

from core.db import init_db

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

# ── Sidebar branding (shown on every page) ──────────────────────────────────
with st.sidebar:
    st.markdown(
        """
        <div style="text-align: center; padding: 0.5rem 0 1rem 0;">
            <div style="font-size: 2.2rem;">🛎️</div>
            <div style="font-size: 1.2rem; font-weight: 700; color: #1B4F8A;">
                Click2Serve
            </div>
            <div style="font-size: 0.8rem; color: #666;">
                Digital service hub
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

# ── Dynamic navigation based on auth state ─────────────────────────────────
def build_nav() -> dict[str, list[st.Page]]:
    customer_pages = [
        st.Page("pages/home.py", title="Home", icon="🏠", default=True),
        st.Page("pages/book.py", title="Book a Service", icon="📝"),
        st.Page("pages/track.py", title="Track Booking", icon="🔍"),
    ]

    if st.session_state.get("logged_in"):
        owner_pages = [
            st.Page("pages/dashboard.py", title="Dashboard", icon="📊"),
            st.Page("pages/bookings.py", title="Bookings", icon="📂"),
            st.Page("pages/revenue.py", title="Revenue", icon="💰"),
            st.Page("pages/logout.py", title="Sign out", icon="🚪"),
        ]
    else:
        owner_pages = [
            st.Page("pages/login.py", title="Owner Login", icon="🔐"),
        ]

    return {
        "Customer": customer_pages,
        "Owner": owner_pages,
    }


nav = st.navigation(build_nav())
nav.run()
