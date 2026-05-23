"""Customer landing page — gradient hero, stats, services grid, CTA banner."""
from __future__ import annotations

import streamlit as st

from core.db import list_categories, list_services
from core.styles import (
    cta_banner, feature_card, hero, how_step, inject_global_css,
    section_header, stat_strip,
)

inject_global_css()

# ── Hero ────────────────────────────────────────────────────────────────────
hero(
    badge="🚀  New · Pay online via UPI",
    title_html=(
        "One shop for every "
        "<span class='c2s-gradient-text'>government &amp; utility</span> "
        "service"
    ),
    subtitle=(
        "Skip the queue. Book passport, driving licence, bills, challans, "
        "photocopying and more — pay from your phone, pick up when ready."
    ),
)

# Hero CTAs sit just below — using real Streamlit buttons so navigation works
hcta1, hcta2, hcta3 = st.columns([1, 1, 1])
with hcta1:
    st.page_link("pages/book.py", label="📝  Book a service", use_container_width=True)
with hcta2:
    st.page_link("pages/track.py", label="🔍  Track booking", use_container_width=True)
with hcta3:
    st.page_link("pages/pay.py", label="💳  Pay online", use_container_width=True)

# Stat strip floats over the hero/cta boundary
all_services = list_services(active_only=True)
all_categories = list_categories()
stat_strip([
    (f"{len(all_services)}+", "Services"),
    (f"{len(all_categories)}", "Categories"),
    ("100%", "UPI ready"),
    ("~24h", "Typical ETA"),
])

# ── Why customers love us (features) ────────────────────────────────────────
section_header(
    eyebrow="Why Click2Serve",
    title="Less waiting. More doing.",
    subtitle="Three things this shop does differently — built so you spend less time at the counter.",
)

f1, f2, f3 = st.columns(3, gap="medium")
with f1:
    feature_card(
        "🚀",
        "Fast turnaround",
        "Most government and bill services completed in 24–48 hours, "
        "with a tracked status from the moment you book.",
    )
with f2:
    feature_card(
        "💳",
        "Pay from your phone",
        "Scan a QR or tap to open PhonePe, GPay, Paytm or any UPI app. "
        "No cash, no card swipe, no extra fees.",
    )
with f3:
    feature_card(
        "🔒",
        "Private &amp; secure",
        "Your documents stay on the shop's local storage. Token + mobile "
        "required to view a booking — no public links, no oversharing.",
    )

# ── How it works ────────────────────────────────────────────────────────────
section_header(
    eyebrow="How it works",
    title="From booking to pickup in three steps",
    subtitle="No queue at the counter. No paperwork printed and re-printed. Just three taps.",
)

s1, s2, s3 = st.columns(3, gap="medium")
with s1:
    how_step(
        1,
        "Book online",
        "Pick the service, fill in your details, and upload any supporting "
        "documents. You'll get a token like <b>C2S-A4F2</b>.",
    )
with s2:
    how_step(
        2,
        "Pay via UPI",
        "Scan the shop's QR code or tap to open your UPI app. Pay the exact "
        "amount and paste the UTR back into the app.",
    )
with s3:
    how_step(
        3,
        "Track &amp; pick up",
        "Watch the status move from <i>Pending</i> to <i>Ready</i>. Walk in "
        "to pick up your finished work — no waiting in line.",
    )

# ── Services catalogue ──────────────────────────────────────────────────────
section_header(
    eyebrow="What we do",
    title="Browse our services",
    subtitle="Government IDs, vehicle services, bill payments, document services — all under one roof.",
)

# Filter row
fc1, fc2 = st.columns([1, 2])
with fc1:
    category_options = ["All categories", *all_categories]
    chosen = st.selectbox("Category", category_options, index=0,
                          label_visibility="collapsed")
with fc2:
    search = st.text_input(
        "Search",
        placeholder="🔎  Search services — passport, electricity, driving licence...",
        label_visibility="collapsed",
    )

# Apply filters
services = all_services
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

st.markdown(
    f'<p style="color:#5C5F7C; margin: 0.4rem 0 1rem; font-weight:500;">'
    f"Showing <b>{len(services)}</b> of {len(all_services)} services"
    f"</p>",
    unsafe_allow_html=True,
)

if not services:
    st.info("No services match your search. Try a different keyword.")
else:
    # 3-column responsive card grid
    for i in range(0, len(services), 3):
        cols = st.columns(3, gap="medium")
        for col, svc in zip(cols, services[i:i + 3]):
            total = svc["govt_fee"] + svc["service_charge"]
            with col:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="c2s-cat">📂  {svc["category"]}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"<div style='font-size:1.05rem; font-weight:700; "
                        f"color:#0A0E27; margin-bottom:0.35rem; line-height:1.3;'>"
                        f"{svc['name']}</div>",
                        unsafe_allow_html=True,
                    )
                    desc = svc["description"]
                    short = desc[:108] + ("…" if len(desc) > 108 else "")
                    st.markdown(
                        f"<div style='color:#5C5F7C; font-size:0.9rem; "
                        f"line-height:1.5; min-height:54px;'>{short}</div>",
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"""
                        <div class="c2s-meta-row">
                            <span class="c2s-pill c2s-pill-price">💰  ₹{total}</span>
                            <span class="c2s-pill c2s-pill-eta">⏱  ~{svc['eta_hours']}h</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Book this service →",
                        key=f"book_{svc['id']}",
                        use_container_width=True,
                        type="primary",
                    ):
                        st.session_state["selected_service_id"] = svc["id"]
                        st.switch_page("pages/book.py")

# ── Closing CTA banner ──────────────────────────────────────────────────────
cta_banner(
    "Ready to skip the queue?",
    "Book any service in under a minute. Pay from your phone. "
    "Pick up when it's ready.",
)

bcta1, bcta2 = st.columns([1, 1])
with bcta1:
    st.page_link("pages/book.py", label="📝  Book a service", use_container_width=True)
with bcta2:
    st.page_link("pages/track.py", label="🔍  Track existing booking",
                 use_container_width=True)
