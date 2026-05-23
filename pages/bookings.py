"""Owner bookings queue — view, filter, update status, mark payment."""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core.db import (
    PAYMENT_METHODS, STATUSES, list_bookings, list_documents,
    update_booking_payment, update_booking_status,
)

if not st.session_state.get("logged_in"):
    st.warning("Please sign in to manage bookings.")
    st.page_link("pages/login.py", label="→ Owner login", use_container_width=True)
    st.stop()

st.title("📂 Bookings Queue")

with st.container(border=True):
    f1, f2, f3, f4 = st.columns([1.5, 1.2, 1.2, 2])
    status_filter = f1.selectbox("Status", ["All", *STATUSES], index=0)
    today = date.today()
    date_from = f2.date_input("From", value=today - timedelta(days=30))
    date_to = f3.date_input("To", value=today)
    search = f4.text_input("Search", placeholder="token, name or phone")

bookings = list_bookings(
    status=status_filter,
    date_from=date_from,
    date_to=date_to,
    search=search or None,
)

if not bookings:
    st.info("No bookings match the current filters.")
    st.stop()

st.caption(f"Showing **{len(bookings)}** booking(s). Newest first.")

# Quick summary table
df = pd.DataFrame([
    {
        "Token": b["token"],
        "Service": b["service_name"],
        "Customer": b["customer_name"],
        "Phone": b["customer_phone"],
        "Status": b["status"],
        "Payment": b["payment_method"],
        "Paid (₹)": b["amount_paid"],
        "Total (₹)": b["total_fee"],
        "Created": b["created_at"].replace("T", " "),
    }
    for b in bookings
])
st.dataframe(df, use_container_width=True, hide_index=True)

st.download_button(
    "⬇️ Export filtered bookings (CSV)",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name=f"click2serve_bookings_{date.today().isoformat()}.csv",
    mime="text/csv",
)

st.markdown("---")
st.subheader("📝 Update a booking")

# Booking selector
labels = {
    b["id"]: f"{b['token']} — {b['service_name']} — {b['customer_name']} ({b['status']})"
    for b in bookings
}
selected_id = st.selectbox(
    "Select booking",
    options=list(labels.keys()),
    format_func=lambda i: labels[i],
)
booking = next(b for b in bookings if b["id"] == selected_id)

with st.container(border=True):
    info_cols = st.columns([1, 1, 1])
    info_cols[0].markdown(f"**Customer**\n\n{booking['customer_name']}\n\n📱 {booking['customer_phone']}")
    info_cols[1].markdown(f"**Service**\n\n{booking['service_name']}\n\n📂 {booking['service_category']}")
    info_cols[2].markdown(
        f"**Fees**\n\nTotal: ₹{booking['total_fee']}\n\n"
        f"Paid: ₹{booking['amount_paid']} ({booking['payment_method']})"
    )

    if booking["customer_email"]:
        st.caption(f"✉️ {booking['customer_email']}")
    if booking["notes"]:
        st.info(f"**Customer notes:** {booking['notes']}")

    docs = list_documents(booking["id"])
    if docs:
        st.markdown("**📎 Attached documents**")
        for d in docs:
            st.write(f"• {d['file_name']}  _({d['size_bytes']:,} bytes)_  → `{d['file_path']}`")

    st.markdown("---")
    st.markdown("**Update status**")

    # One-click status flow buttons
    flow_cols = st.columns(len(STATUSES))
    for col, status in zip(flow_cols, STATUSES):
        is_current = (booking["status"] == status)
        label = ("✓ " if is_current else "") + status
        if col.button(label, key=f"status_{status}", use_container_width=True,
                      disabled=is_current,
                      type="primary" if status == "Ready" and not is_current else "secondary"):
            update_booking_status(booking["id"], status)
            st.success(f"Status updated to **{status}**.")
            st.rerun()

    st.markdown("---")
    st.markdown("**Mark payment**")
    p1, p2, p3 = st.columns([1.2, 1.2, 1])
    new_method = p1.selectbox("Method", PAYMENT_METHODS,
                              index=PAYMENT_METHODS.index(booking["payment_method"])
                              if booking["payment_method"] in PAYMENT_METHODS else 0)
    new_amount = p2.number_input(
        "Amount paid (₹)", min_value=0,
        value=int(booking["amount_paid"] or booking["total_fee"]),
        step=10,
    )
    if p3.button("💾 Save payment", use_container_width=True, type="primary"):
        update_booking_payment(booking["id"], method=new_method,
                               amount=int(new_amount))
        st.success("Payment updated.")
        st.rerun()
