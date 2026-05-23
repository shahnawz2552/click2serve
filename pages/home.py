"""Customer landing page — hero + service catalogue."""
from __future__ import annotations

import streamlit as st

from core.db import list_categories, list_services

st.markdown(
    """
    <div style="
        background: linear-gradient(135deg, #1B4F8A 0%, #2E6FB5 100%);
        padding: 2.5rem 2rem; border-radius: 12px; color: white;
        margin-bottom: 1.5rem;">
        <h1 style="color: white; margin: 0 0 0.4rem 0;">Click2Serve</h1>
        <p style="font-size: 1.1rem; margin: 0; opacity: 0.95;">
            Your one-click digital service hub —
            passport, driving licence, bills, challans, document services and more.
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3 = st.columns(3)
c1.markdown("### 🚀\nFast turnaround")
c1.caption("Most services completed within 24–48 hours.")
c2.markdown("### 🔒\nSecure & private")
c2.caption("Your documents are stored locally and never shared.")
c3.markdown("### 💬\nReal-time tracking")
c3.caption("Track your booking status with a token number.")

st.markdown("---")

# Category filter
categories = ["All categories", *list_categories()]
chosen = st.selectbox("Filter by category", categories, index=0)
search = st.text_input(
    "Search services",
    placeholder="e.g. passport, electricity, driving licence...",
    label_visibility="collapsed",
)

services = list_services(active_only=True)
if chosen != "All categories":
    services = [s for s in services if s["category"] == chosen]
if search:
    needle = search.lower()
    services = [
        s for s in services
        if needle in s["name"].lower()
        or needle in s["description"].lower()
        or needle in s["category"].lower()
    ]

st.subheader(f"📋 {len(services)} services available")

if not services:
    st.info("No services match your search. Try a different keyword.")
else:
    # 3-column responsive card grid
    for i in range(0, len(services), 3):
        cols = st.columns(3)
        for col, svc in zip(cols, services[i:i + 3]):
            total = svc["govt_fee"] + svc["service_charge"]
            with col:
                with st.container(border=True):
                    st.markdown(f"**{svc['name']}**")
                    st.caption(f"📂  {svc['category']}")
                    st.write(svc["description"][:110] + ("…" if len(svc["description"]) > 110 else ""))
                    st.markdown(
                        f"<div style='display:flex; gap:1rem; font-size:0.85rem; "
                        f"color:#444; margin: 0.4rem 0;'>"
                        f"<span>💰 <b>₹{total}</b></span>"
                        f"<span>⏱ ~{svc['eta_hours']}h</span>"
                        f"</div>",
                        unsafe_allow_html=True,
                    )
                    if st.button("Book this", key=f"book_{svc['id']}", use_container_width=True):
                        st.session_state["selected_service_id"] = svc["id"]
                        st.switch_page("pages/book.py")

st.markdown("---")
b1, b2 = st.columns(2)
b1.page_link("pages/book.py", label="📝  Book a Service", use_container_width=True)
b2.page_link("pages/track.py", label="🔍  Track Existing Booking", use_container_width=True)
