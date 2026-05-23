"""Customer tracking page — look up a booking by token + phone."""
from __future__ import annotations

import streamlit as st

from core.db import get_booking_by_token, list_documents
from core.styles import inject_global_css, section_header

inject_global_css()

STATUS_BADGES = {
    "Pending": ("🟡", "We have received your request and will start shortly."),
    "In Progress": ("🔵", "Your work is being processed by the shop owner."),
    "Ready": ("🟢", "Your work is ready for pick-up. Please visit the shop."),
    "Delivered": ("✅", "Booking completed and handed over. Thank you!"),
    "Cancelled": ("❌", "This booking was cancelled. Please contact the shop for details."),
}

section_header(
    eyebrow="Track booking",
    title="Where's my service at?",
    subtitle="Enter your token and the mobile number you used at booking.",
)

with st.form("track_form"):
    c1, c2 = st.columns(2)
    token = c1.text_input("Token number *", placeholder="e.g. C2S-A1B2", max_chars=20)
    phone = c2.text_input(
        "Mobile number *",
        placeholder="The number used at booking",
        max_chars=10,
        help="We ask for your number to keep your booking private.",
    )
    submitted = st.form_submit_button("Track", type="primary",
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

    badge, message = STATUS_BADGES.get(booking["status"], ("ℹ️", booking["status"]))

    with st.container(border=True):
        st.markdown(f"### Token: `{booking['token']}`")
        st.caption(f"Booked on {booking['created_at'].replace('T', ' ')}")

        st.markdown(f"## {badge}  {booking['status']}")
        st.write(message)

        st.markdown("---")
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
        if pstatus == "submitted":
            st.warning(
                "⏳ Your payment is awaiting verification by the shop owner. "
                f"UTR on file: **{booking['payment_ref']}**."
            )
        elif pstatus == "verified":
            st.success("✅ Payment verified.")
        elif pstatus == "rejected":
            st.error("Your last payment proof was rejected. Please retry the payment.")

        # Show the Pay-now CTA when there's still money owed
        if booking["amount_paid"] < total or pstatus in ("rejected", "unpaid"):
            st.session_state["pay_token"] = booking["token"]
            st.session_state["pay_phone"] = booking["customer_phone"]
            st.page_link("pages/pay.py",
                         label="💳  Pay online now",
                         use_container_width=True)

        # Documents (file names only — no public download for privacy)
        docs = list_documents(booking["id"])
        if docs:
            st.markdown("**📎 Documents on file**")
            for d in docs:
                st.write(f"• {d['file_name']}")

        if booking["notes"]:
            st.markdown("**Your notes**")
            st.info(booking["notes"])

st.markdown("---")
st.page_link("pages/home.py", label="← Back to home", use_container_width=False)
