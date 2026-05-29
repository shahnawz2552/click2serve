"""Click2Serve — main entry point.

Customers see only customer-facing pages. The owner login is hidden behind
a discreet "Owner" button at the bottom of the sidebar — clicking it
reveals the owner login page. Once logged in, owner pages are shown; on
logout they disappear again.

Sidebar starts collapsed so the home page lands cleanly on mobile.
"""
#from __future__ import annotations

import streamlit as st

from core.db import init_db
from core.seo import google_traffic_banner, inject_local_business_jsonld
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
    initial_sidebar_state="auto",  # expanded on desktop, collapsed on mobile
    menu_items={
        "Get help": None,
        "Report a bug": None,
        "About": "Click2Serve — Your one-click digital service hub.",
    },
)

# ── Apply the global stylesheet to every page ───────────────────────────────
inject_global_css()

# ── Local business structured data — drives the Google Maps "Book Now" button.
# Emitted on every page so any URL the shop shares (root, /book, /contact)
# can serve as the canonical landing for Google to crawl.
inject_local_business_jsonld()

# ── Welcome banner for traffic arriving via Google Business Profile ─────────
# Detects ``?utm_source=google`` so we can warmly greet walk-by Maps users.
google_traffic_banner()


def _owner_route_visible() -> bool:
    """Return True when the owner section should appear in the sidebar.

    True if the user is already signed in, or if they've clicked the
    discreet "Owner" button at the bottom of the sidebar (which sets
    ``show_owner_login`` in session state).
    """
    if st.session_state.get("logged_in"):
        return True
    return bool(st.session_state.get("show_owner_login"))


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


# ── Dynamic navigation based on auth + sidebar state ──────────────────────
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
        st.Page("pages/contact.py", title="Contact us",
                icon=":material/call:"),
    ]

    pages: dict[str, list[st.Page]] = {"Customer": customer_pages}

    if st.session_state.get("logged_in"):
        pages["Owner"] = [
            st.Page("pages/dashboard.py", title="Dashboard",
                    icon="📊"),
            st.Page("pages/bookings.py", title="Bookings",
                    icon="📁"),
            st.Page("pages/services.py", title="Services",
                    icon="🛠️"),
            st.Page("pages/revenue.py", title="Revenue",
                    icon="💰"),
            st.Page("pages/settings.py", title="Settings",
                    icon="⚙️"),
            st.Page("pages/logout.py", title="Sign out",
                    icon="🚪"),
        ]
    elif _owner_route_visible():
        pages["Owner"] = [
            st.Page("pages/login.py", title="Owner login",
                    icon="🔒"),
        ]

    return pages


nav = st.navigation(build_nav())

# ── Pending page-switch handler ───────────────────────────────────────────
# Some sidebar buttons need to (a) flip a session-state flag and (b) jump
# straight to a different page once the navigation has been rebuilt to
# include that page. We can't call st.switch_page in the same run that
# adds the page to the nav (the nav is locked at the st.navigation(...)
# call above), so the button stashes the destination in session state and
# triggers st.rerun(); on the next run, build_nav() now includes the
# destination page, and we can safely switch to it here.
_pending_target = st.session_state.pop("_pending_page_switch", None)
if _pending_target == "login":
    st.switch_page("pages/login.py")
elif _pending_target == "home":
    st.switch_page("pages/home.py")


# ── Discreet "Owner" button at the bottom of the sidebar ──────────────────
# Streamlit renders sidebar widgets in code order, so anything appended to
# the sidebar after st.navigation(...) appears below the nav links.
with st.sidebar:
    # Spacer pushes the button toward the bottom of the sidebar on tall
    # screens without forcing it off-screen on short ones.
    st.markdown(
        "<div style='height: 1.4rem;'></div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='border-top: 1px solid {BORDER}; "
        f"margin: 0 -0.25rem 0.6rem;'></div>",
        unsafe_allow_html=True,
    )

    if not st.session_state.get("logged_in"):
        if st.session_state.get("show_owner_login"):
            # Already revealed — let the user dismiss the login form.
            if st.button(
                "Hide owner login",
                key="hide_owner_btn",
                use_container_width=True,
                help="Go back to the customer-only view.",
            ):
                st.session_state.pop("show_owner_login", None)
                # Send the user back to home on the next run, after the
                # Owner section has been removed from the nav.
                st.session_state["_pending_page_switch"] = "home"
                st.rerun()
        else:
            # Discreet, link-styled trigger so it doesn't fight for
            # attention with the customer nav above.
            if st.button(
                "Owner",
                key="reveal_owner_btn",
                use_container_width=True,
                help="Shop owners and staff: click to sign in.",
            ):
                st.session_state["show_owner_login"] = True
                # Jump straight to the login page on the next run, so the
                # user sees the sign-in form immediately instead of a new
                # nav entry they then have to click.
                st.session_state["_pending_page_switch"] = "login"
                st.rerun()

        st.markdown(
            f"<div style='color:{MUTED}; font-size:0.72rem; text-align:center; "
            f"margin-top:0.4rem;'>Customers don't need to sign in.</div>",
            unsafe_allow_html=True,
        )


nav.run()
