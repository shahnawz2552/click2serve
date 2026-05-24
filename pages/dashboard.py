"""Owner dashboard — KPI cards, pending-verifications alert, quick actions."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core.auth import change_password
from core.db import (
    pending_verification_count, revenue_by_service, today_kpis,
)
from core.styles import (
    BORDER, DANGER, DANGER_BG, DANGER_TEXT, INK, MUTED, PRIMARY, SUCCESS,
    SURFACE, WARNING, inject_global_css, kpi_card, section_header,
)

inject_global_css()

if not st.session_state.get("logged_in"):
    st.warning("Please sign in to access the owner dashboard.")
    st.page_link("pages/login.py", label="Owner login →",
                 use_container_width=True)
    st.stop()

section_header(
    eyebrow="Owner",
    title=f"Welcome back, {st.session_state.get('username', 'owner').title()}.",
    subtitle="Today's queue, today's revenue, and anything that needs your "
             "attention.",
)


# ── Pending-verifications alert (red banner at top) ────────────────────────
pending_verif = pending_verification_count()
if pending_verif:
    st.markdown(
        f"<div style='background:{DANGER_BG}; border:1px solid {DANGER}; "
        f"border-left:4px solid {DANGER}; border-radius:12px; padding:"
        f"0.9rem 1rem; margin-bottom:1.1rem; display:flex; align-items:"
        f"center; justify-content:space-between; gap:0.8rem;'>"
        f"<div>"
        f"<div style='font-weight:700; color:{DANGER_TEXT}; font-size:0.95rem;'>"
        f"🔔  {pending_verif} online payment(s) awaiting verification</div>"
        f"<div style='color:{DANGER_TEXT}; font-size:0.85rem; opacity:0.9; "
        f"margin-top:0.15rem;'>Open Bookings to confirm them in your UPI app."
        f"</div>"
        f"</div>"
        f"</div>",
        unsafe_allow_html=True,
    )


# ── KPI cards (4 columns) ───────────────────────────────────────────────────
kpis = today_kpis()

m1, m2, m3, m4 = st.columns(4, gap="small")
m1.markdown(
    kpi_card("📥", str(kpis["total"]), "Today's bookings", PRIMARY),
    unsafe_allow_html=True,
)
m2.markdown(
    kpi_card("⏳", str(kpis["pending"]), "Pending", WARNING),
    unsafe_allow_html=True,
)
m3.markdown(
    kpi_card("💰", f"₹{kpis['revenue']:,}", "Revenue today", SUCCESS),
    unsafe_allow_html=True,
)
m4.markdown(
    kpi_card("✅", str(kpis["delivered"]), "Total delivered", "#0F766E"),
    unsafe_allow_html=True,
)


# ── Quick actions ───────────────────────────────────────────────────────────
st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)

q1, q2, q3 = st.columns(3, gap="small")
with q1:
    st.page_link("pages/bookings.py", label="View Queue →",
                 use_container_width=True)
with q2:
    st.page_link("pages/revenue.py", label="Revenue Report →",
                 use_container_width=True)
with q3:
    st.page_link("pages/settings.py", label="Settings →",
                 use_container_width=True)


# ── Top services (last 7 days) ──────────────────────────────────────────────
st.markdown("<div style='height:1.4rem;'></div>", unsafe_allow_html=True)

end = date.today()
start = end - timedelta(days=6)
top = revenue_by_service(start, end)

with st.container(border=True):
    st.markdown(
        f"<div style='font-size:0.95rem; font-weight:700; color:{INK}; "
        f"margin-bottom:0.6rem;'>Top services · last 7 days</div>",
        unsafe_allow_html=True,
    )
    if not top:
        st.markdown(
            f"<div style='color:{MUTED}; font-size:0.9rem;'>"
            "No bookings in the last 7 days yet.</div>",
            unsafe_allow_html=True,
        )
    else:
        df = pd.DataFrame([dict(r) for r in top]).head(8)
        df = df.rename(columns={
            "service_name": "Service",
            "bookings": "Bookings",
            "revenue": "Revenue (₹)",
        })
        st.dataframe(df, use_container_width=True, hide_index=True)


# ── Change password (advanced, in expander) ─────────────────────────────────
with st.expander("Change owner password"):
    with st.form("pwd_form"):
        new_pw = st.text_input("New password", type="password",
                               help="At least 6 characters.")
        confirm = st.text_input("Confirm new password", type="password")
        save = st.form_submit_button("Update password", type="primary")
    if save:
        if len(new_pw) < 6:
            st.error("Password must be at least 6 characters.")
        elif new_pw != confirm:
            st.error("Passwords do not match.")
        else:
            change_password(st.session_state["username"], new_pw)
            st.success("Password updated. Please sign in again next time.")
