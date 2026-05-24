"""Customer landing page — editorial hero, trust badges, services grid, CTA."""
from __future__ import annotations

import streamlit as st

from core.db import list_categories, list_services
from core.styles import (
    cta_banner, hero, how_step, inject_global_css,
    section_header,
)

inject_global_css()

# ── Hero ────────────────────────────────────────────────────────────────────
hero(
    badge="Click2Serve · Digital service hub",
    title_html=(
        "Fast, reliable "
        "<span class='c2s-accent'>digital services</span> "
        "at your "
        "<span class='c2s-italic'>doorstep</span>."
    ),
    subtitle=(
        "Skip the queue. Book passport, driving licence, bills, challans and "
        "photocopying — pay from your phone, pick up when ready."
    ),
)

# Hero CTAs
hcta1, hcta2, hcta3, _ = st.columns([1, 1, 1, 2])
with hcta1:
    st.page_link("pages/book.py", label="Book a service →",
                 use_container_width=True)
with hcta2:
    st.page_link("pages/track.py", label="Track booking",
                 use_container_width=True)
with hcta3:
    st.page_link("pages/pay.py", label="Pay online",
                 use_container_width=True)

st.markdown("<div style='height:1.4rem;'></div>", unsafe_allow_html=True)

# ── Trust signals ───────────────────────────────────────────────────────────
all_services = list_services(active_only=True)
all_categories = list_categories()

t1, t2, t3 = st.columns(3, gap="medium")
with t1:
    with st.container(border=True):
        st.markdown(
            "<div class='c2s-cat'>Trust signal · 01</div>"
            "<div style='font-size:1.6rem; font-weight:900; "
            "letter-spacing:-0.03em; color:#0E120F; line-height:1.1;'>"
            "🔒 Secure Payments</div>"
            "<div style='color:#5A6157; margin-top:0.4rem; "
            "font-size:0.93rem; line-height:1.5;'>"
            "UPI-only flow with end-to-end traceability via UTR. No card "
            "data ever touches our servers.</div>",
            unsafe_allow_html=True,
        )
with t2:
    with st.container(border=True):
        st.markdown(
            f"<div class='c2s-cat'>Trust signal · 02</div>"
            f"<div style='font-size:1.6rem; font-weight:900; "
            f"letter-spacing:-0.03em; color:#0E120F; line-height:1.1;'>"
            f"📋 {max(len(all_services), 12)}+ Services</div>"
            f"<div style='color:#5A6157; margin-top:0.4rem; "
            f"font-size:0.93rem; line-height:1.5;'>"
            f"Government IDs, vehicle services, bill payments, document "
            f"work — all under one roof.</div>",
            unsafe_allow_html=True,
        )
with t3:
    with st.container(border=True):
        st.markdown(
            "<div class='c2s-cat'>Trust signal · 03</div>"
            "<div style='font-size:1.6rem; font-weight:900; "
            "letter-spacing:-0.03em; color:#0E120F; line-height:1.1;'>"
            "⚡ Same-day Processing</div>"
            "<div style='color:#5A6157; margin-top:0.4rem; "
            "font-size:0.93rem; line-height:1.5;'>"
            "Bills and documents complete in hours. Govt applications "
            "submitted same business day.</div>",
            unsafe_allow_html=True,
        )

# ── How it works ────────────────────────────────────────────────────────────
section_header(
    eyebrow="How it works",
    title="From booking to pickup in three steps.",
    subtitle="No queue. No paperwork printed and re-printed. Just three taps.",
)

s1, s2, s3 = st.columns(3, gap="medium")
with s1:
    how_step(
        1, "Book online",
        "Pick the service, fill in your details, and upload any supporting "
        "documents. You'll get a token like <b>C2S-A4F2</b>.",
    )
with s2:
    how_step(
        2, "Pay via UPI",
        "Scan the shop's QR code or tap to open your UPI app. Pay the exact "
        "amount and paste the UTR back into the app.",
    )
with s3:
    how_step(
        3, "Track &amp; pick up",
        "Watch the status move from <i>Pending</i> to <i>Ready</i>. Walk in "
        "to pick up your finished work — no waiting in line.",
    )

# ── Services catalogue ──────────────────────────────────────────────────────
section_header(
    eyebrow="What we do",
    title="Browse our services.",
    subtitle="Government IDs, vehicle services, bill payments, "
             "document services — all under one roof.",
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
        placeholder="Search services — passport, electricity, driving licence…",
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
    f'<p style="color:#5A6157; margin: 0.4rem 0 1rem; font-weight:500; '
    f'font-size:0.92rem; letter-spacing:0.01em;">'
    f"Showing <b style='color:#0E120F;'>{len(services)}</b> of "
    f"{len(all_services)} services"
    f"</p>",
    unsafe_allow_html=True,
)

if not services:
    st.info("No services match your search. Try a different keyword.")
else:
    for i in range(0, len(services), 3):
        cols = st.columns(3, gap="medium")
        for col, svc in zip(cols, services[i:i + 3]):
            total = (svc["govt_fee"] or 0) + (svc["service_charge"] or 0)
            with col:
                with st.container(border=True):
                    st.markdown(
                        f'<div class="c2s-cat">{svc["category"]}</div>'
                        f'<div class="c2s-svc-name">{svc["name"]}</div>',
                        unsafe_allow_html=True,
                    )
                    desc = svc.get("description") or ""
                    short = desc[:108] + ("…" if len(desc) > 108 else "")
                    st.markdown(
                        f'<div class="c2s-svc-desc">{short}</div>',
                        unsafe_allow_html=True,
                    )
                    st.markdown(
                        f"""
                        <div class="c2s-meta-row">
                            <span class="c2s-pill"><span class="c2s-pill-label">Fee</span>₹{total}</span>
                            <span class="c2s-pill"><span class="c2s-pill-label">ETA</span>~{svc['eta_hours']}h</span>
                        </div>
                        """,
                        unsafe_allow_html=True,
                    )
                    if st.button(
                        "Book Now →",
                        key=f"book_{svc['id']}",
                        use_container_width=True,
                        type="primary",
                    ):
                        # Pass the service via URL — book.py reads it from
                        # st.query_params on load.
                        st.query_params["service"] = str(svc["id"])
                        st.session_state["selected_service_id"] = svc["id"]
                        st.switch_page("pages/book.py")

# ── Closing CTA banner ──────────────────────────────────────────────────────
cta_banner(
    eyebrow="Ready to skip the queue?",
    title_html=(
        "Book any service in "
        "<span class='c2s-accent'>under a minute</span>."
    ),
    subtitle="Pay from your phone. Pick up when it's ready. That's it.",
)

bcta1, bcta2, _ = st.columns([1, 1, 2])
with bcta1:
    st.page_link("pages/book.py", label="Book a service →",
                 use_container_width=True)
with bcta2:
    st.page_link("pages/track.py", label="Track existing booking",
                 use_container_width=True)
