"""Customer landing page — hero, trust badges, service grid."""
from __future__ import annotations

import streamlit as st

from core.db import list_categories, list_services
from core.styles import (
    BORDER, INK, MUTED, PRIMARY, SURFACE, category_badge,
    inject_global_css, trust_badge,
)

inject_global_css()


# ── Hero ────────────────────────────────────────────────────────────────────
st.markdown(
    f"""
    <div style="text-align:center; padding:1.4rem 0 0.8rem;">
        <div style="font-size:3rem; line-height:1;">🛎️</div>
        <h1 style="font-size:2rem !important; font-weight:800 !important;
                   margin:0.6rem 0 0.3rem !important; color:{INK} !important;
                   letter-spacing:-0.02em;">
            Click2Serve
        </h1>
        <p style="color:{MUTED}; font-size:0.95rem; margin:0;">
            Fast · Reliable · Digital Services
        </p>
    </div>
    <hr style="border:none; border-top:1px solid {BORDER};
               margin:1rem 0 1.2rem;"/>
    """,
    unsafe_allow_html=True,
)


# ── Trust badges ────────────────────────────────────────────────────────────
all_services = list_services(active_only=True)
all_categories = list_categories()

t1, t2, t3 = st.columns(3, gap="small")
with t1:
    st.markdown(trust_badge("🔒", "Secure"), unsafe_allow_html=True)
with t2:
    st.markdown(
        trust_badge("📋", f"{max(len(all_services), 12)}+ Services"),
        unsafe_allow_html=True,
    )
with t3:
    st.markdown(trust_badge("⚡", "Same Day"), unsafe_allow_html=True)


# ── Above-the-fold owner link ───────────────────────────────────────────────
# Tiny, top-right link so shop owners can always find sign-in immediately on
# landing — no sidebar required, no scrolling required. Customers can ignore.
if not st.session_state.get("logged_in"):
    _, owner_col = st.columns([5, 1])
    with owner_col:
        if st.button(
            "Owner →",
            key="home_owner_top_btn",
            use_container_width=True,
            help="Shop owners and staff: click to sign in.",
        ):
            st.session_state["show_owner_login"] = True
            st.session_state["_pending_page_switch"] = "login"
            st.rerun()


# ── Filter row ──────────────────────────────────────────────────────────────
st.markdown(
    "<div style='height:1.2rem;'></div>"
    f"<h2 style='font-size:1.05rem !important; font-weight:700 !important; "
    f"margin:0 0 0.6rem !important;'>Browse services</h2>",
    unsafe_allow_html=True,
)

fc1, fc2 = st.columns([1, 2])
with fc1:
    category_options = ["All categories", *all_categories]
    chosen = st.selectbox("Category", category_options, index=0,
                          label_visibility="collapsed")
with fc2:
    search = st.text_input(
        "Search",
        placeholder="Search — passport, electricity, driving licence…",
        label_visibility="collapsed",
    )

services = all_services
if chosen != "All categories":
    services = [s for s in services if s["category"] == chosen]
if search:
    needle = search.lower()
    services = [
        s for s in services
        if needle in s["name"].lower()
        or needle in (s.get("description") or "").lower()
        or needle in s["category"].lower()
    ]

st.markdown(
    f'<p style="color:{MUTED}; margin:0.5rem 0 1rem; font-weight:500; '
    f'font-size:0.85rem;">'
    f"Showing <b style='color:{INK};'>{len(services)}</b> of "
    f"{len(all_services)} services"
    f"</p>",
    unsafe_allow_html=True,
)


# ── Service grid (3 cols desktop, 1 col mobile via Streamlit responsive) ───
if not services:
    st.info("No services match your search. Try a different keyword.")
else:
    for i in range(0, len(services), 3):
        cols = st.columns(3, gap="small")
        for col, svc in zip(cols, services[i:i + 3]):
            total = (svc["govt_fee"] or 0) + (svc["service_charge"] or 0)
            with col:
                with st.container(border=True):
                    st.markdown(
                        f'<div style="display:flex; align-items:center; '
                        f'justify-content:space-between; gap:0.6rem; '
                        f'margin-bottom:0.5rem;">'
                        f'{category_badge(svc["category"])}'
                        f'<span style="color:{MUTED}; font-size:0.8rem; '
                        f'font-weight:500;">⏱️ {svc["eta_hours"]}h</span>'
                        f'</div>'
                        f'<div style="font-size:1rem; font-weight:700; '
                        f'color:{INK}; line-height:1.3; '
                        f'margin-bottom:0.5rem; min-height:2.6rem;">'
                        f'{svc["name"]}</div>'
                        f'<div class="c2s-price" style="margin-bottom:0.8rem;">'
                        f'₹{total}</div>',
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Book Now →",
                        key=f"book_{svc['id']}",
                        use_container_width=True,
                        type="primary",
                    ):
                        st.query_params["service"] = str(svc["id"])
                        st.session_state["selected_service_id"] = svc["id"]
                        st.switch_page("pages/book.py")


# ── Footer CTA ──────────────────────────────────────────────────────────────
st.markdown("<div style='height:1.6rem;'></div>", unsafe_allow_html=True)

ft1, ft2, ft3 = st.columns(3)
with ft1:
    st.page_link("pages/track.py", label="Track booking",
                 use_container_width=True)
with ft2:
    st.page_link("pages/pay.py", label="Pay online",
                 use_container_width=True)
with ft3:
    st.page_link("pages/contact.py", label="Contact us",
                 use_container_width=True)


# ── Discreet owner-access link ─────────────────────────────────────────────
# Mirrors the "Owner" button at the bottom of the sidebar so mobile users
# with the sidebar collapsed can still find their way to the login page.
# Intentionally small / muted so it doesn't compete with the customer CTAs.
st.markdown(
    f"<div style='height: 2.2rem;'></div>"
    f"<div style='border-top:1px solid {BORDER}; "
    f"margin: 0 -0.5rem 0.8rem;'></div>",
    unsafe_allow_html=True,
)

if not st.session_state.get("logged_in"):
    of1, of2, of3 = st.columns([1, 1, 1])
    with of2:
        if st.button(
            "Owner",
            key="home_owner_btn",
            use_container_width=True,
            help="Shop owners and staff: click to sign in.",
        ):
            # Same pending-switch handshake as the sidebar button in app.py:
            # we can't switch directly to login.py because it isn't in the
            # current st.navigation (we are about to add it). Set the flag
            # and rerun — app.py's pending-switch handler will take over and
            # call st.switch_page once the nav has been rebuilt.
            st.session_state["show_owner_login"] = True
            st.session_state["_pending_page_switch"] = "login"
            st.rerun()
        st.markdown(
            f"<div style='color:{MUTED}; font-size:0.7rem; text-align:center; "
            f"margin-top:0.3rem;'>Customers don't need to sign in.</div>",
            unsafe_allow_html=True,
        )
