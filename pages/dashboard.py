"""Owner dashboard — today's KPIs and quick links."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core.auth import change_password
from core.db import pending_verification_count, revenue_by_service, today_kpis
from core.styles import inject_global_css, section_header

inject_global_css()

if not st.session_state.get("logged_in"):
    st.warning("Please sign in to access the owner dashboard.")
    st.page_link("pages/login.py", label="Owner login →",
                 use_container_width=True)
    st.stop()

section_header(
    eyebrow="Owner",
    title=f"Welcome back, {st.session_state.get('username', 'owner').title()}.",
    subtitle="Today's queue, today's revenue, and anything that needs your attention.",
)

# Surface pending UPI verifications immediately — this is the highest-priority
# thing an owner needs to act on each day.
pending_verif = pending_verification_count()
if pending_verif:
    st.warning(
        f"**{pending_verif} online payment(s) awaiting your verification.** "
        "Open Bookings to confirm them in your UPI app."
    )

kpis = today_kpis()

m1, m2, m3, m4 = st.columns(4)
m1.metric("Today's bookings", f"{kpis['total']}")
m2.metric("Pending", f"{kpis['pending']}",
          help="Bookings awaiting work to start.")
m3.metric("Ready for pickup", f"{kpis['ready']}",
          help="Customer can be notified now.")
m4.metric("Today's revenue", f"₹{kpis['revenue']:,}")

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)

# This week's top services
end = date.today()
start = end - timedelta(days=6)
top = revenue_by_service(start, end)

col_a, col_b = st.columns([2, 1])

with col_a:
    st.markdown(
        "<div class='c2s-cat'>Top services · last 7 days</div>"
        "<h3 style='margin:0 0 1rem;'>Where the work is coming from.</h3>",
        unsafe_allow_html=True,
    )
    if not top:
        st.caption("No bookings in the last 7 days yet.")
    else:
        df = pd.DataFrame([dict(r) for r in top]).head(8)
        df = df.rename(columns={
            "service_name": "Service",
            "bookings": "Bookings",
            "revenue": "Revenue (₹)",
        })
        st.dataframe(df, use_container_width=True, hide_index=True)

with col_b:
    st.markdown(
        "<div class='c2s-cat'>Quick links</div>"
        "<h3 style='margin:0 0 0.8rem;'>Jump to.</h3>",
        unsafe_allow_html=True,
    )
    st.page_link("pages/bookings.py", label="Manage bookings →",
                 use_container_width=True)
    st.page_link("pages/revenue.py", label="Revenue report →",
                 use_container_width=True)
    st.page_link("pages/settings.py", label="Shop settings →",
                 use_container_width=True)
    st.page_link("pages/home.py", label="Customer view",
                 use_container_width=True)

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)

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
