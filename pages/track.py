"""Customer tracking page — single booking by token + phone, OR list all
bookings tied to a phone number (lightweight repeat-customer access).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from core.db import get_booking_by_token, list_bookings, list_documents
from core.styles import (
    BORDER, INK, MUTED, PRIMARY, SURFACE, inject_global_css, payment_badge,
    section_header, status_badge, status_timeline,
)

inject_global_css()

STATUS_MESSAGE = {
    "Pending":     "We have received your request and will start shortly.",
    "In Progress": "Your work is being processed by the shop owner.",
    "Ready":       "Your work is ready for pick-up. Please visit the shop.",
    "Delivered":   "Booking completed and handed over. Thank you.",
    "Cancelled":   "This booking was cancelled. Please contact the shop.",
}

section_header(
    eyebrow="Track booking",
    title="Where is my service?",
    subtitle="Look up one booking by its token, or every booking tied to "
             "your mobile number.",
)


# ── Centered search form (mobile-first single column) ──────────────────────
tab_one, tab_all = st.tabs(["Look up a token", "My bookings (by phone)"])


def _eta_text(booking: dict) -> str:
    """Return a friendly 'estimated by' string given created_at + ETA hours."""
    try:
        created = datetime.fromisoformat(
            (booking.get("created_at") or "").replace("Z", "+00:00")
        )
    except ValueError:
        return ""
    eta_h = booking.get("eta_hours") or 0
    eta_dt = created + timedelta(hours=int(eta_h))
    return eta_dt.strftime("%a %d %b · %I:%M %p").replace(" 0", " ")


# ── TAB 1: single booking by token + phone ─────────────────────────────────
with tab_one:
    with st.container(border=True):
        with st.form("track_form"):
            st.markdown(
                f"<div style='font-size:0.85rem; font-weight:600; color:{INK}; "
                f"margin-bottom:0.6rem;'>🔍  Find a booking</div>",
                unsafe_allow_html=True,
            )
            c1, c2 = st.columns(2)
            token = c1.text_input("Token number", placeholder="C2S-XXXX",
                                  max_chars=20)
            phone = c2.text_input(
                "Mobile number",
                placeholder="The number used at booking",
                max_chars=10,
                help="We ask for your number to keep your booking private.",
            )
            submitted = st.form_submit_button("Track booking →",
                                              type="primary",
                                              use_container_width=True)

    if submitted:
        if not token.strip() or not phone.strip():
            st.error("Please provide both token and mobile number.")
            st.stop()

        booking = get_booking_by_token(token, phone)
        if not booking:
            st.error(
                "No booking found with that token + mobile combination. "
                "Double-check the token or contact the shop owner."
            )
            st.stop()

        # ── Header card (token + status pill) ───────────────────────────
        with st.container(border=True):
            st.markdown(
                f"<div style='display:flex; align-items:center; "
                f"justify-content:space-between; gap:0.6rem; flex-wrap:wrap;'>"
                f"<div>"
                f"<div style='font-size:0.74rem; font-weight:600; color:{MUTED}; "
                f"text-transform:uppercase; letter-spacing:0.06em;'>Token</div>"
                f"<div class='c2s-token' style='margin-top:0.2rem;'>"
                f"{booking['token']}</div>"
                f"</div>"
                f"<div>{status_badge(booking['status'], big=True)}</div>"
                f"</div>"
                f"<div style='color:{MUTED}; font-size:0.82rem; margin-top:0.6rem;'>"
                f"{STATUS_MESSAGE.get(booking['status'], booking['status'])}"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:1rem;'></div>",
                    unsafe_allow_html=True)

        # ── Timeline ────────────────────────────────────────────────────
        st.markdown(status_timeline(booking["status"]), unsafe_allow_html=True)

        eta = _eta_text(booking)
        if eta and booking["status"] not in ("Delivered", "Cancelled"):
            st.markdown(
                f"<div style='text-align:center; color:{MUTED}; font-size:"
                f"0.85rem; margin-top:0.6rem;'>"
                f"Estimated ready by <b style='color:{INK};'>{eta}</b>"
                f"</div>",
                unsafe_allow_html=True,
            )

        # ── Booking details ─────────────────────────────────────────────
        st.markdown("<div style='height:1rem;'></div>",
                    unsafe_allow_html=True)
        with st.container(border=True):
            d1, d2, d3 = st.columns(3)
            d1.metric("Service", booking["service_name"])
            d2.metric("Category", booking["service_category"])
            total = (booking["govt_fee"] or 0) + (booking["service_charge"] or 0)
            d3.metric("Total fee", f"₹{total}")

            p1, p2 = st.columns(2)
            p1.metric("Payment method", booking["payment_method"])
            p2.metric("Amount paid", f"₹{booking['amount_paid']}")

            st.markdown(
                "<div style='margin-top:0.4rem;'>"
                + payment_badge(booking.get("payment_status") or "unpaid")
                + "</div>",
                unsafe_allow_html=True,
            )

        # ── Pay-now CTA when there's still money owed ──────────────────
        pstatus = booking.get("payment_status") or "unpaid"
        if booking["amount_paid"] < total or pstatus in ("rejected", "unpaid"):
            st.session_state["pay_token"] = booking["token"]
            st.session_state["pay_phone"] = booking["customer_phone"]
            st.markdown("<div style='height:0.8rem;'></div>",
                        unsafe_allow_html=True)
            st.page_link("pages/pay.py", label="Pay online now →",
                         use_container_width=True)

        if pstatus == "submitted":
            st.warning(
                f"Your payment is awaiting verification by the shop owner. "
                f"UTR on file: **{booking.get('payment_ref')}**."
            )
        elif pstatus == "rejected":
            st.error("Your last payment proof was rejected. Please retry.")

        # ── Documents ──────────────────────────────────────────────────
        docs = list_documents(booking["id"])
        if docs:
            st.markdown("<div style='height:1rem;'></div>",
                        unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(
                    f"<div style='font-size:0.78rem; font-weight:700; "
                    f"color:{INK}; text-transform:uppercase; letter-spacing:"
                    f"0.06em; margin-bottom:0.5rem;'>Documents on file</div>",
                    unsafe_allow_html=True,
                )
                for d in docs:
                    st.markdown(
                        f"<div style='color:{INK}; font-size:0.9rem; "
                        f"padding:0.2rem 0;'>📎  {d['file_name']}</div>",
                        unsafe_allow_html=True,
                    )

        if booking.get("notes"):
            st.markdown("<div style='height:0.8rem;'></div>",
                        unsafe_allow_html=True)
            st.info(booking["notes"])


# ── TAB 2: list all bookings by phone ──────────────────────────────────────
with tab_all:
    st.markdown(
        f"<p style='color:{MUTED}; font-size:0.9rem;'>"
        "Returning customer? Enter your phone number to see every booking "
        "you've made — no login or token required.</p>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        with st.form("history_form"):
            history_phone = st.text_input(
                "Mobile number", placeholder="10-digit mobile",
                max_chars=10, key="history_phone_input",
            )
            history_submitted = st.form_submit_button(
                "Show my bookings →", type="primary",
                use_container_width=True,
            )

    if history_submitted:
        if not history_phone.strip():
            st.error("Please enter your mobile number.")
            st.stop()

        rows = list_bookings(phone=history_phone.strip(), limit=200)
        if not rows:
            st.info("No bookings found for this number.")
            st.stop()

        st.success(f"Found **{len(rows)}** booking(s) tied to this number.")

        df = pd.DataFrame([
            {
                "Token": r["token"],
                "Service": r["service_name"],
                "Status": r["status"],
                "Paid (₹)": r["amount_paid"],
                "Total (₹)": (r["govt_fee"] or 0) + (r["service_charge"] or 0),
                "Created": (r["created_at"] or "").replace("T", " ")[:19],
            }
            for r in rows
        ])
        st.dataframe(df, use_container_width=True, hide_index=True)

        st.markdown(
            f"<p style='color:{MUTED}; font-size:0.85rem; margin-top:0.6rem;'>"
            "To open a specific booking, copy its token to the "
            "<b>Look up a token</b> tab above.</p>",
            unsafe_allow_html=True,
        )
