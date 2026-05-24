"""Customer tracking page — single booking by token + phone, OR list all
bookings tied to a phone number (lightweight repeat-customer access).
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.db import get_booking_by_token, list_bookings, list_documents
from core.styles import (
    inject_global_css, payment_badge, section_header, status_badge,
)

inject_global_css()

STATUS_MESSAGE = {
    "Pending":     "We have received your request and will start shortly.",
    "In Progress": "Your work is being processed by the shop owner.",
    "Ready":       "Your work is ready for pick-up. Please visit the shop.",
    "Delivered":   "Booking completed and handed over. Thank you.",
    "Cancelled":   "This booking was cancelled. Please contact the shop for details.",
}

section_header(
    eyebrow="Track booking",
    title="Where is my service?",
    subtitle="Look up one booking by its token, or every booking tied to "
             "your mobile number — no login required.",
)

tab_one, tab_all = st.tabs(["Look up a token", "My bookings (by phone)"])


# ── TAB 1: single booking by token + phone ─────────────────────────────────
with tab_one:
    with st.form("track_form"):
        c1, c2 = st.columns(2)
        token = c1.text_input("Token number", placeholder="C2S-XXXX",
                              max_chars=20)
        phone = c2.text_input(
            "Mobile number",
            placeholder="The number used at booking",
            max_chars=10,
            help="We ask for your number to keep your booking private.",
        )
        submitted = st.form_submit_button("Track →", type="primary",
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

        message = STATUS_MESSAGE.get(booking["status"], booking["status"])

        with st.container(border=True):
            st.markdown(
                f"<div class='c2s-cat'>Token</div>"
                f"<div style='font-size:1.7rem; font-weight:900; "
                f"letter-spacing:-0.03em; color:#0E120F; line-height:1; "
                f"margin-bottom:0.3rem;'>{booking['token']}</div>"
                f"<div style='font-size:0.82rem; color:#5A6157;'>"
                f"Booked on {(booking['created_at'] or '').replace('T', ' ')[:19]}</div>",
                unsafe_allow_html=True,
            )

            st.markdown("<hr class='c2s-rule' style='margin:1.4rem 0 1rem;'/>",
                        unsafe_allow_html=True)
            st.markdown(status_badge(booking["status"], big=True),
                        unsafe_allow_html=True)
            st.markdown(
                f"<p style='color:#5A6157; margin-top:0.6rem;'>{message}</p>",
                unsafe_allow_html=True,
            )

            st.markdown("<hr class='c2s-rule' style='margin:1.6rem 0 1rem;'/>",
                        unsafe_allow_html=True)
            info = st.columns(3)
            info[0].metric("Service", booking["service_name"])
            info[1].metric("Category", booking["service_category"])
            total = (booking["govt_fee"] or 0) + (booking["service_charge"] or 0)
            info[2].metric("Total fee", f"₹{total}")

            pay_cols = st.columns(2)
            pay_cols[0].metric("Payment method", booking["payment_method"])
            pay_cols[1].metric("Amount paid", f"₹{booking['amount_paid']}")

            pstatus = booking.get("payment_status") or "unpaid"
            st.markdown(
                "<div style='margin-top:0.8rem;'>"
                + payment_badge(pstatus) + "</div>",
                unsafe_allow_html=True,
            )

            if pstatus == "submitted":
                st.warning(
                    f"Your payment is awaiting verification by the shop owner. "
                    f"UTR on file: **{booking.get('payment_ref')}**."
                )
            elif pstatus == "rejected":
                st.error(
                    "Your last payment proof was rejected. "
                    "Please retry the payment."
                )

            if booking["amount_paid"] < total or pstatus in ("rejected", "unpaid"):
                st.session_state["pay_token"] = booking["token"]
                st.session_state["pay_phone"] = booking["customer_phone"]
                st.page_link("pages/pay.py",
                             label="Pay online now →",
                             use_container_width=True)

            docs = list_documents(booking["id"])
            if docs:
                st.markdown(
                    "<hr class='c2s-rule' style='margin:1.4rem 0 0.8rem;'/>"
                    "<div class='c2s-cat'>Documents on file</div>",
                    unsafe_allow_html=True,
                )
                for d in docs:
                    st.write(f"— {d['file_name']}")

            if booking.get("notes"):
                st.markdown(
                    "<hr class='c2s-rule' style='margin:1.4rem 0 0.8rem;'/>"
                    "<div class='c2s-cat'>Your notes</div>",
                    unsafe_allow_html=True,
                )
                st.info(booking["notes"])


# ── TAB 2: all bookings by phone ───────────────────────────────────────────
with tab_all:
    st.caption(
        "Returning customer? Enter your phone number to see every booking "
        "you've made — no login or token required."
    )
    with st.form("history_form"):
        history_phone = st.text_input(
            "Mobile number", placeholder="10-digit mobile",
            max_chars=10, key="history_phone_input",
        )
        history_submitted = st.form_submit_button(
            "Show my bookings →", type="primary", use_container_width=True,
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
            "<p style='color:#5A6157; font-size:0.9rem; margin-top:0.6rem;'>"
            "To open a specific booking, switch to the <b>Look up a token</b> "
            "tab and paste the token above.</p>",
            unsafe_allow_html=True,
        )


st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.page_link("pages/home.py", label="← Back to home",
             use_container_width=False)
