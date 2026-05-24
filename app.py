"""Click2Serve — main entry point.

Customers see only customer-facing pages. The owner login is hidden behind
a special URL — visit ``?owner=1`` to reveal it. Once logged in, owner
pages are shown; on logout they disappear again.

Sidebar starts collapsed so the home page lands cleanly on mobile.
"""
from __future__ import annotations

import streamlit as st

from core.db import init_db
from core.styles import (
    BORDER, INK, MUTED, PRIMARY, PRIMARY_TINT, SURFACE, inject_global_css,
)

# ── Bootstrap database on first request (Supabase) ──────────────────────────
init_db()

# ── Page config (only the entry point sets this) ────────────────────────────
st.set_page_config(
    page_title="Click2Serve — Digital Service Hub",
    page_icon="🛎️",
    layout="wide",
    initial_sidebar_state="collapsed",  # mobile-first
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": "Click2Serve — Your one-click digital service hub.",
    },
)

# ── Apply the global stylesheet to every page ───────────────────────────────
inject_global_css()


def _owner_route_visible() -> bool:
    """Owner login is shown only when the URL contains the magic flag.

    Once an owner is signed in, we keep the owner pages visible for the
    duration of the session — even if they navigate away from the magic
    URL.
    """
    if st.session_state.get("logged_in"):
        return True
    raw = st.query_params.get("owner")
    if raw is None:
        return False
    if isinstance(raw, list):
        raw = raw[0] if raw else ""
    return str(raw).lower() not in ("0", "false", "no")


# ── Sidebar branding (white, no gradient) ──────────────────────────────────
with st.sidebar:
    st.markdown(
        f"""
        <div style="
            display: flex; align-items: center; gap: 0.65rem;
            padding: 0.4rem 0 1.4rem 0;
            border-bottom: 1px solid {BORDER}; margin-bottom: 0.8rem;">
          <div style="
              width: 36px; height: 36px;
              border-radius: 10px;
              background: {PRIMARY_TINT};
              color: {PRIMARY};
              display: inline-flex; align-items: center; justify-content: center;
              font-size: 1.2rem;
          ">🛎️</div>
          <div>
            <div style="font-size: 1.05rem; font-weight: 700;
                        letter-spacing: -0.01em; color: {INK}; line-height: 1.1;">
              Click2Serve
            </div>
            <div style="font-size: 0.74rem; color: {MUTED};
                        font-weight: 500; margin-top: 0.15rem;">
              Digital service hub
            </div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# ── Dynamic navigation based on auth + URL state ──────────────────────────
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

    pages: dict[str, list[st.Page]] = {"Customer": customer_pages}

    if st.session_state.get("logged_in"):
        pages["Owner"] = [
            st.Page("pages/dashboard.py", title="Dashboard",
                    icon=":material/dashboard:"),
            st.Page("pages/bookings.py", title="Bookings",
                    icon=":material/folder_open:"),
            st.Page("pages/services.py", title="Services",
                    icon=":material/miscellaneous_services:"),
            st.Page("pages/revenue.py", title="Revenue",
                    icon=":material/savings:"),
            st.Page("pages/settings.py", title="Settings",
                    icon=":material/tune:"),
            st.Page("pages/logout.py", title="Sign out",
                    icon=":material/logout:"),
        ]
    elif _owner_route_visible():
        pages["Owner"] = [
            st.Page("pages/login.py", title="Owner login",
                    icon=":material/lock:"),
        ]

    return pages


nav = st.navigation(build_nav())
nav.run()
