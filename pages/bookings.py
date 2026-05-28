"""Owner bookings queue — view, filter, update status, mark payment.

When the owner changes a booking's status, we fire a WhatsApp alert to
the customer's phone via core.notifications. The alert is best-effort
and never blocks the actual update.
"""
from __future__ import annotations

from datetime import date, timedelta

import pandas as pd
import streamlit as st

from core.db import (
    PAYMENT_METHODS, STATUSES, list_bookings, list_documents,
    reject_payment, update_booking_payment, update_booking_status,
    verify_payment,
)
from core.notifications import notify_status_change
from core.styles import (
    inject_global_css, payment_badge, section_header, status_badge,
)

inject_global_css()

if not st.session_state.get("logged_in"):
    st.warning("Please sign in to manage bookings.")
    st.page_link("pages/login.py", label="Owner login →",
                 use_container_width=True)
    st.stop()

section_header(
    eyebrow="Owner · Queue",
    title="Bookings.",
    subtitle="Filter, update statuses, verify online payments — "
             "everything from one screen.",
)


# ── Helpers — read row fields safely ─────────────────────────────────────
def _g(b: dict, key: str, default=""):
    """Like dict.get but coerces None to the default (sentinel-friendly)."""
    val = b.get(key) if isinstance(b, dict) else None
    return default if val is None else val


def _gint(b: dict, key: str, default: int = 0) -> int:
    try:
        return int(_g(b, key, default) or 0)
    except (TypeError, ValueError):
        return default


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
) or []

if not bookings:
    st.info("No bookings match the current filters.")
    st.stop()

st.markdown(
    f"<p style='color:#5A6157; margin:0.6rem 0 1rem; font-weight:500;'>"
    f"Showing <b style='color:#0E120F;'>{len(bookings)}</b> booking(s). "
    f"Newest first.</p>",
    unsafe_allow_html=True,
)

# Quick summary table — every column read defensively so a single missing
# field on one row doesn't blow up the whole page with a KeyError.
df = pd.DataFrame([
    {
        "Token": _g(b, "token", "—"),
        "Service": _g(b, "service_name", "—"),
        "Customer": _g(b, "customer_name", "—"),
        "Phone": _g(b, "customer_phone", ""),
        "Status": _g(b, "status", "Pending"),
        "Payment": _g(b, "payment_method", "Unpaid"),
        "Pay status": _g(b, "payment_status", "unpaid"),
        "Paid (₹)": _gint(b, "amount_paid", 0),
        "Total (₹)": _gint(b, "total_fee", 0),
        "Created": str(_g(b, "created_at", "")).replace("T", " ")[:19],
    }
    for b in bookings
])
st.dataframe(df, use_container_width=True, hide_index=True)

st.download_button(
    "Export filtered bookings — CSV",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name=f"click2serve_bookings_{date.today().isoformat()}.csv",
    mime="text/csv",
)

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.markdown(
    "<div class='c2s-cat'>Detail · Update</div>"
    "<h3 style='margin:0 0 1rem;'>Open a booking.</h3>",
    unsafe_allow_html=True,
)


# Booking selector — surface unverified UPI bookings first by sorting them up
def _selector_label(b: dict) -> str:
    flag = " ⚠ unverified UPI" if _g(b, "payment_status") == "submitted" else ""
    return (
        f"{_g(b, 'token', '—')} — {_g(b, 'service_name', '—')} — "
        f"{_g(b, 'customer_name', '—')} ({_g(b, 'status', 'Pending')}){flag}"
    )


# Sort: unverified-UPI first, then newest-first within each group
sorted_bookings = sorted(
    bookings,
    key=lambda b: (
        _g(b, "payment_status") != "submitted",
        -_gint(b, "id", 0),
    ),
)
labels = {_g(b, "id"): _selector_label(b) for b in sorted_bookings if _g(b, "id") != ""}

if not labels:
    st.info("No bookings to open.")
    st.stop()

selected_id = st.selectbox(
    "Select booking",
    options=list(labels.keys()),
    format_func=lambda i: labels[i],
)
booking = next((b for b in bookings if _g(b, "id") == selected_id), None)
if booking is None:
    st.error("Could not load this booking. Please reload the page.")
    st.stop()

with st.container(border=True):
    info_cols = st.columns([1, 1, 1])
    info_cols[0].markdown(
        f"<div class='c2s-cat'>Customer</div>"
        f"<div style='font-weight:700; font-size:1.05rem;'>"
        f"{_g(booking, 'customer_name', '—')}</div>"
        f"<div style='color:#5A6157; font-size:0.9rem;'>"
        f"{_g(booking, 'customer_phone', '')}</div>",
        unsafe_allow_html=True,
    )
    info_cols[1].markdown(
        f"<div class='c2s-cat'>Service</div>"
        f"<div style='font-weight:700; font-size:1.05rem;'>"
        f"{_g(booking, 'service_name', '—')}</div>"
        f"<div style='color:#5A6157; font-size:0.9rem;'>"
        f"{_g(booking, 'service_category', '')}</div>",
        unsafe_allow_html=True,
    )
    info_cols[2].markdown(
        f"<div class='c2s-cat'>Fees</div>"
        f"<div style='font-weight:700; font-size:1.05rem;'>"
        f"Total ₹{_gint(booking, 'total_fee', 0)}</div>"
        f"<div style='color:#5A6157; font-size:0.9rem;'>"
        f"Paid ₹{_gint(booking, 'amount_paid', 0)} "
        f"({_g(booking, 'payment_method', 'Unpaid')})</div>",
        unsafe_allow_html=True,
    )

    if _g(booking, "customer_email"):
        st.caption(f"Email: {booking['customer_email']}")
    if _g(booking, "notes"):
        st.info(f"**Customer notes:** {booking['notes']}")

    docs = list_documents(_g(booking, "id")) or []
    if docs:
        st.markdown(
            "<div class='c2s-cat' style='margin-top:0.8rem;'>"
            "Attached documents</div>",
            unsafe_allow_html=True,
        )
        for d in docs:
            size = _gint(d, "size_bytes", 0)
            st.write(
                f"— {_g(d, 'file_name', 'file')}  _({size:,} bytes)_  "
                f"→ `{_g(d, 'file_path', '')}`"
            )

    st.markdown("<hr class='c2s-rule' style='margin:1.6rem 0 1rem;'/>",
                unsafe_allow_html=True)
    current_status = _g(booking, "status", "Pending")
    st.markdown(
        f"<div style='display:flex; align-items:center; "
        f"justify-content:space-between; margin-bottom:0.8rem;'>"
        f"<span class='c2s-cat' style='margin:0;'>Status</span>"
        f"{status_badge(current_status)}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # One-click status flow buttons
    flow_cols = st.columns(len(STATUSES))
    for col, status in zip(flow_cols, STATUSES):
        is_current = (current_status == status)
        label = ("✓ " if is_current else "") + status
        if col.button(label, key=f"status_{status}", use_container_width=True,
                      disabled=is_current,
                      type=("primary"
                            if status == "Ready" and not is_current
                            else "secondary")):
            update_booking_status(_g(booking, "id"), status)
            # Fire a WhatsApp notification (best-effort, never blocks).
            sent = False
            try:
                sent = notify_status_change(
                    token=_g(booking, "token", ""),
                    status=status,
                    customer_name=_g(booking, "customer_name", ""),
                    customer_phone=_g(booking, "customer_phone", ""),
                )
            except Exception:
                pass  # already logged inside notify_status_change

            msg = f"Status updated to **{status}**."
            if sent:
                msg += " WhatsApp alert sent to your phone."
            elif status in ("In Progress", "Ready", "Delivered", "Cancelled"):
                msg += (" (WhatsApp alert was not sent — see Settings → "
                        "Customer notifications.)")
            st.success(msg)
            st.rerun()

    st.markdown("<hr class='c2s-rule' style='margin:1.6rem 0 1rem;'/>",
                unsafe_allow_html=True)
    pay_status = _g(booking, "payment_status", "unpaid")
    st.markdown(
        f"<div style='display:flex; align-items:center; "
        f"justify-content:space-between; margin-bottom:0.8rem;'>"
        f"<span class='c2s-cat' style='margin:0;'>Payment</span>"
        f"{payment_badge(pay_status)}"
        f"</div>",
        unsafe_allow_html=True,
    )

    # If the customer submitted a UTR online, surface it for one-click verify.
    if pay_status == "submitted":
        st.warning(
            "**Online payment awaiting verification.**  \n"
            f"Customer paid via UPI · UTR  `{_g(booking, 'payment_ref', '')}` · "
            f"Amount  ₹{_gint(booking, 'amount_paid', 0)}"
        )
        st.caption(
            "Open your UPI app and look for an incoming credit matching this "
            "UTR / amount. If it's there, click **Verify**. Otherwise click "
            "**Reject** and the customer will be prompted to retry."
        )
        v1, v2 = st.columns(2)
        if v1.button("Verify payment →", key="verify_btn",
                     use_container_width=True, type="primary"):
            verify_payment(_g(booking, "id"))
            st.success("Payment verified. Customer will see the confirmation.")
            st.rerun()
        if v2.button("Reject payment proof", key="reject_btn",
                     use_container_width=True):
            reject_payment(_g(booking, "id"))
            st.warning("Payment proof rejected. Customer can retry.")
            st.rerun()
        st.markdown("<hr class='c2s-rule' style='margin:1.4rem 0 1rem;'/>",
                    unsafe_allow_html=True)
        st.caption(
            "Or override manually below if you collected cash / card directly."
        )
    elif pay_status == "verified":
        ref = _g(booking, "payment_ref")
        st.success(
            f"Payment verified · ₹{_gint(booking, 'amount_paid', 0)} via "
            f"{_g(booking, 'payment_method', 'Unpaid')}"
            + (f" · UTR `{ref}`" if ref else "")
        )

    p1, p2, p3 = st.columns([1.2, 1.2, 1])
    current_method = _g(booking, "payment_method", "Unpaid")
    method_index = (
        PAYMENT_METHODS.index(current_method)
        if current_method in PAYMENT_METHODS else 0
    )
    new_method = p1.selectbox("Method", PAYMENT_METHODS, index=method_index)
    new_amount = p2.number_input(
        "Amount paid (₹)", min_value=0,
        value=_gint(booking, "amount_paid", 0)
              or _gint(booking, "total_fee", 0),
        step=10,
    )
    if p3.button("Save payment", use_container_width=True, type="primary"):
        update_booking_payment(
            _g(booking, "id"),
            method=new_method,
            amount=int(new_amount),
        )
        st.success("Payment updated.")
        st.rerun()
