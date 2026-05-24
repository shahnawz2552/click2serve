"""Click2Serve — main entry point."""
from _future_ import annotations

import streamlit as st
from core.db import init_db
from core.styles import inject_global_css

init_db()

st.set_page_config(
    page_title="Click2Serve — Digital Service Hub",
    page_icon="🛎️",
    layout="wide",
    initial_sidebar_state="collapsed",
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": "Click2Serve — Your one-click digital service hub.",
    },
)

inject_global_css()

with st.sidebar:
    st.markdown(
        """
        <div style="padding: 0.4rem 0 1.6rem 0;">
        <span style="font-size: 1.05rem; font-weight: 800;">🛎️ click2serve</span>
        <div style="font-size: 0.7rem; color: #5A6157; margin-top: 0.5rem;">
        Digital service hub</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

def build_nav() -> dict[str, list[st.Page]]:
    customer_pages = [
        st.Page("pages/home.py", title="Home", icon="🏠", default=True),
        st.Page("pages/book.py", title="Book a service", icon="📝"),
        st.Page("pages/pay.py", title="Pay online", icon="💳"),
        st.Page("pages/track.py", title="Track booking", icon="🔍"),
    ]

    if st.session_state.get("logged_in"):
        owner_pages = [
            st.Page("pages/dashboard.py", title="Dashboard", icon="📊"),
            st.Page("pages/bookings.py", title="Bookings", icon="📁"),
            st.Page("pages/revenue.py", title="Revenue", icon="💰"),
            st.Page("pages/settings.py", title="Settings", icon="⚙️"),
            st.Page("pages/logout.py", title="Sign out", icon="🚪"),
        ]
    else:
        owner_pages = [
            st.Page("pages/login.py", title="Owner login", icon="🔒"),
        ]

    return {
        "Customer": customer_pages,
        "Owner": owner_pages,
    }

nav = st.navigation(build_nav())
nav.run()