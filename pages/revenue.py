"""Owner revenue report — KPIs, daily trend, service breakdown, CSV export."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core.db import revenue_by_day, revenue_by_service, revenue_summary
from core.styles import inject_global_css, section_header

inject_global_css()

if not st.session_state.get("logged_in"):
    st.warning("Please sign in to view the revenue report.")
    st.page_link("pages/login.py", label="Owner login →",
                 use_container_width=True)
    st.stop()

section_header(
    eyebrow="Owner · Reports",
    title="Revenue.",
    subtitle="Track earnings by day and by service. Export anything to CSV.",
)

# Date range presets
today = date.today()
preset = st.radio(
    "Range",
    ["Today", "Last 7 days", "Last 30 days", "This month", "Custom"],
    horizontal=True,
)

if preset == "Today":
    start, end = today, today
elif preset == "Last 7 days":
    start, end = today - timedelta(days=6), today
elif preset == "Last 30 days":
    start, end = today - timedelta(days=29), today
elif preset == "This month":
    start, end = today.replace(day=1), today
else:
    c1, c2 = st.columns(2)
    start = c1.date_input("From", value=today - timedelta(days=30))
    end = c2.date_input("To", value=today)

if start > end:
    st.error("Start date must be on or before end date.")
    st.stop()

st.caption(f"Showing data from **{start}** to **{end}**.")

summary = revenue_summary(start, end)

m1, m2, m3, m4 = st.columns(4)
m1.metric("Total bookings", f"{summary['total_bookings']}")
m2.metric("Revenue collected", f"₹{summary['revenue']:,}")
m3.metric("Delivered", f"{summary['delivered']}")
m4.metric("Unpaid", f"{summary['unpaid']}",
          help="Bookings without a recorded payment yet.")

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)

# Daily trend
daily = revenue_by_day(start, end)
df_daily = pd.DataFrame([dict(r) for r in daily])

if df_daily.empty:
    st.info("No bookings in this range.")
else:
    df_daily["day"] = pd.to_datetime(df_daily["day"])
    df_daily = df_daily.set_index("day").sort_index()

    st.markdown(
        "<div class='c2s-cat'>Daily revenue</div>"
        "<h3 style='margin:0 0 0.8rem;'>What you collected, day by day.</h3>",
        unsafe_allow_html=True,
    )
    st.bar_chart(df_daily["revenue"], height=260, color="#0E120F")

    st.markdown(
        "<div class='c2s-cat' style='margin-top:1.4rem;'>Daily bookings</div>"
        "<h3 style='margin:0 0 0.8rem;'>Volume of work taken in.</h3>",
        unsafe_allow_html=True,
    )
    st.bar_chart(df_daily["bookings"], height=220, color="#9FC95D")

# Per-service breakdown
st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.markdown(
    "<div class='c2s-cat'>Service breakdown</div>"
    "<h3 style='margin:0 0 0.8rem;'>Where the revenue came from.</h3>",
    unsafe_allow_html=True,
)

by_service = revenue_by_service(start, end)
df_svc = pd.DataFrame([dict(r) for r in by_service])

if df_svc.empty:
    st.caption("No service data for this period.")
else:
    df_svc = df_svc.rename(columns={
        "service_name": "Service",
        "bookings": "Bookings",
        "revenue": "Revenue (₹)",
    })
    st.dataframe(df_svc, use_container_width=True, hide_index=True)

    st.download_button(
        "Download CSV",
        data=df_svc.to_csv(index=False).encode("utf-8"),
        file_name=f"click2serve_revenue_{start}_to_{end}.csv",
        mime="text/csv",
    )
