"""Customer tracking page — single booking by token + phone, OR list all
bookings tied to a phone number (lightweight repeat-customer access).
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pandas as pd
import streamlit as st

from core.db import (
    get_booking_by_token, list_bookings, list_documents,
    signed_document_url,
)
from core.styles import (
    BORDER, INK, MUTED, PRIMARY, SURFACE, floating_book_button,
    inject_global_css, payment_badge,
    section_header, status_badge, status_timeline,
)

inject_global_css()

from core.visitor import track_session_visit
track_session_visit()

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


# ── Defensive row-reading helpers ────────────────────────────────────────
# Booking rows from Supabase can have NULL columns or be missing newer
# fields entirely. Reading via [] then crashes the page. These helpers
# treat any missing field as a safe default.
def _r(row: dict, key: str, default=""):
    val = row.get(key) if isinstance(row, dict) else None
    return default if val is None else val


def _rint(row: dict, key: str, default: int = 0) -> int:
    try:
        return int(_r(row, key, default) or 0)
    except (TypeError, ValueError):
        return default


# ── Centered search form (mobile-first single column) ──────────────────────
tab_one, tab_all = st.tabs(["Look up a token", "My bookings (by phone)"])


def _eta_text(booking: dict) -> str:
    """Return a friendly 'estimated by' string given created_at + ETA hours."""
    try:
        created = datetime.fromisoformat(
            (_r(booking, "created_at", "") or "").replace("Z", "+00:00")
        )
    except ValueError:
        return ""
    eta_h = _rint(booking, "eta_hours", 0)
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

        booking_status = _r(booking, "status", "Pending")
        booking_token = _r(booking, "token", "—")

        # ── Header card (token + status pill) ───────────────────────────
        with st.container(border=True):
            st.markdown(
                f"<div style='display:flex; align-items:center; "
                f"justify-content:space-between; gap:0.6rem; flex-wrap:wrap;'>"
                f"<div>"
                f"<div style='font-size:0.74rem; font-weight:600; color:{MUTED}; "
                f"text-transform:uppercase; letter-spacing:0.06em;'>Token</div>"
                f"<div class='c2s-token' style='margin-top:0.2rem;'>"
                f"{booking_token}</div>"
                f"</div>"
                f"<div>{status_badge(booking_status, big=True)}</div>"
                f"</div>"
                f"<div style='color:{MUTED}; font-size:0.82rem; margin-top:0.6rem;'>"
                f"{STATUS_MESSAGE.get(booking_status, booking_status)}"
                f"</div>",
                unsafe_allow_html=True,
            )

        st.markdown("<div style='height:1rem;'></div>",
                    unsafe_allow_html=True)

        # ── Timeline ────────────────────────────────────────────────────
        st.markdown(status_timeline(booking_status), unsafe_allow_html=True)

        eta = _eta_text(booking)
        if eta and booking_status not in ("Delivered", "Cancelled"):
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
            d1.metric("Service", _r(booking, "service_name", "—"))
            d2.metric("Category", _r(booking, "service_category", "—"))
            total = _rint(booking, "govt_fee", 0) + \
                _rint(booking, "service_charge", 0)
            d3.metric("Total fee", f"₹{total}")

            p1, p2 = st.columns(2)
            p1.metric("Payment method", _r(booking, "payment_method", "Unpaid"))
            p2.metric("Amount paid", f"₹{_rint(booking, 'amount_paid', 0)}")

            st.markdown(
                "<div style='margin-top:0.4rem;'>"
                + payment_badge(_r(booking, "payment_status", "unpaid"))
                + "</div>",
                unsafe_allow_html=True,
            )

        # ── Pay-now CTA when there's still money owed ──────────────────
        pstatus = _r(booking, "payment_status", "unpaid")
        amount_paid = _rint(booking, "amount_paid", 0)
        if amount_paid < total or pstatus in ("rejected", "unpaid"):
            st.session_state["pay_token"] = booking_token
            st.session_state["pay_phone"] = _r(booking, "customer_phone", "")
            st.markdown("<div style='height:0.8rem;'></div>",
                        unsafe_allow_html=True)
            st.page_link("pages/pay.py", label="Pay online now →",
                         use_container_width=True)

        if pstatus == "submitted":
            st.warning(
                f"Your payment is awaiting verification by the shop owner. "
                f"UTR on file: **{_r(booking, 'payment_ref', '')}**."
            )
        elif pstatus == "rejected":
            st.error("Your last payment proof was rejected. Please retry.")

        # ── Documents ──────────────────────────────────────────────────
        booking_id = _r(booking, "id", None)
        docs = list_documents(booking_id) if booking_id is not None else []
        if docs:
            st.markdown("<div style='height:1rem;'></div>",
                        unsafe_allow_html=True)
            with st.container(border=True):
                st.markdown(
                    f"<div style='font-size:0.78rem; font-weight:700; "
                    f"color:{INK}; text-transform:uppercase; letter-spacing:"
                    f"0.06em; margin-bottom:0.6rem;'>Your documents on file"
                    f"</div>",
                    unsafe_allow_html=True,
                )
                IMG_EXTS = (".jpg", ".jpeg", ".png", ".webp", ".gif")
                for d in docs:
                    file_name = _r(d, "file_name", "file")
                    file_path = _r(d, "file_path", "")
                    file_type = (_r(d, "file_type", "") or "").lower()
                    is_image = (
                        file_type.startswith("image/")
                        or file_name.lower().endswith(IMG_EXTS)
                    )
                    url = (
                        signed_document_url(file_path) if file_path else None
                    )
                    cols = st.columns([3, 1])
                    cols[0].markdown(
                        f"<div style='color:{INK}; font-size:0.9rem; "
                        f"padding:0.2rem 0;'>"
                        f"{'🖼️' if is_image else '📎'} {file_name}</div>",
                        unsafe_allow_html=True,
                    )
                    if url:
                        cols[1].link_button(
                            "View ↗", url, use_container_width=True,
                        )
                    if url and is_image:
                        try:
                            st.image(url, width=320)
                        except Exception:  # noqa: BLE001
                            pass

        if _r(booking, "notes"):
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

        rows = list_bookings(phone=history_phone.strip(), limit=200) or []
        if not rows:
            st.info("No bookings found for this number.")
            st.stop()

        st.success(f"Found **{len(rows)}** booking(s) tied to this number.")

        df = pd.DataFrame([
            {
                "Token": _r(r, "token", "—"),
                "Service": _r(r, "service_name", "—"),
                "Status": _r(r, "status", "Pending"),
                "Paid (₹)": _rint(r, "amount_paid", 0),
                "Total (₹)": _rint(r, "govt_fee", 0)
                              + _rint(r, "service_charge", 0),
                "Created": str(_r(r, "created_at", "")).replace("T", " ")[:19],
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



if not st.session_state.get("logged_in"):
    floating_book_button()
