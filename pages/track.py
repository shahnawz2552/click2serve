"""Customer tracking page — look up a booking by token + phone."""
from __future__ import annotations

import streamlit as st

from core.db import get_booking_by_token, list_documents
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
    subtitle="Enter your token and the mobile number you used at booking.",
)

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
        st.error("No booking found with that token + mobile combination. "
                 "Double-check the token or contact the shop owner.")
        st.stop()

    message = STATUS_MESSAGE.get(booking["status"], booking["status"])

    with st.container(border=True):
        st.markdown(
            f"<div class='c2s-cat'>Token</div>"
            f"<div style='font-size:1.7rem; font-weight:900; "
            f"letter-spacing:-0.03em; color:#0E120F; line-height:1; "
            f"margin-bottom:0.3rem;'>{booking['token']}</div>"
            f"<div style='font-size:0.82rem; color:#5A6157;'>"
            f"Booked on {booking['created_at'].replace('T', ' ')}</div>",
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
        total = booking["govt_fee"] + booking["service_charge"]
        info[2].metric("Total fee", f"₹{total}")

        pay_cols = st.columns(2)
        pay_cols[0].metric("Payment method", booking["payment_method"])
        pay_cols[1].metric("Amount paid", f"₹{booking['amount_paid']}")

        # Surface the payment-verification status with a useful next action
        pstatus = booking["payment_status"] or "unpaid"
        st.markdown(
            "<div style='margin-top:0.8rem;'>"
            + payment_badge(pstatus) + "</div>",
            unsafe_allow_html=True,
        )

        if pstatus == "submitted":
            st.warning(
                f"Your payment is awaiting verification by the shop owner. "
                f"UTR on file: **{booking['payment_ref']}**."
            )
        elif pstatus == "rejected":
            st.error(
                "Your last payment proof was rejected. Please retry the payment."
            )

        # Show the Pay-now CTA when there's still money owed
        if booking["amount_paid"] < total or pstatus in ("rejected", "unpaid"):
            st.session_state["pay_token"] = booking["token"]
            st.session_state["pay_phone"] = booking["customer_phone"]
            st.page_link("pages/pay.py",
                         label="Pay online now →",
                         use_container_width=True)

        # Documents (file names only — no public download for privacy)
        docs = list_documents(booking["id"])
        if docs:
            st.markdown(
                "<hr class='c2s-rule' style='margin:1.4rem 0 0.8rem;'/>"
                "<div class='c2s-cat'>Documents on file</div>",
                unsafe_allow_html=True,
            )
            for d in docs:
                st.write(f"— {d['file_name']}")

        if booking["notes"]:
            st.markdown(
                "<hr class='c2s-rule' style='margin:1.4rem 0 0.8rem;'/>"
                "<div class='c2s-cat'>Your notes</div>",
                unsafe_allow_html=True,
            )
            st.info(booking["notes"])

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.page_link("pages/home.py", label="← Back to home",
             use_container_width=False)
