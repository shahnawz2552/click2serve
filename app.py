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
        <div style="text-align: center; padding: 0.6rem 0 1.4rem 0;">
            <div style="
                width: 56px; height: 56px;
                border-radius: 16px;
                background: linear-gradient(135deg, #7B68EE 0%, #FB3F8C 100%);
                display: inline-flex; align-items: center; justify-content: center;
                font-size: 1.7rem;
                margin-bottom: 0.6rem;
                box-shadow: 0 8px 22px rgba(123,104,238,0.32);
            ">🛎️</div>
            <div style="font-size: 1.25rem; font-weight: 800; letter-spacing: -0.02em; color: #0A0E27;">
                Click2Serve
            </div>
            <div style="font-size: 0.78rem; color: #5C5F7C; font-weight: 500;">
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
        st.Page("pages/pay.py", title="Pay Online", icon="💳"),
        st.Page("pages/track.py", title="Track Booking", icon="🔍"),
    ]

    if st.session_state.get("logged_in"):
        owner_pages = [
            st.Page("pages/dashboard.py", title="Dashboard", icon="📊"),
            st.Page("pages/bookings.py", title="Bookings", icon="📂"),
            st.Page("pages/revenue.py", title="Revenue", icon="💰"),
            st.Page("pages/settings.py", title="Settings", icon="⚙️"),
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
