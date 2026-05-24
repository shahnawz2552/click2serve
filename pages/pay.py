"""Customer payment page — UPI deep link + QR + UTR submission."""
from __future__ import annotations

import streamlit as st

from core.db import (
    get_booking_by_token,
    get_shop_config,
    submit_payment_proof,
)
from core.payments import (
    build_upi_uri,
    is_valid_utr,
    is_valid_vpa,
    qr_svg,
)
from core.styles import inject_global_css, section_header

inject_global_css()

section_header(
    eyebrow="Pay online",
    title="Fast, secure UPI payment.",
    subtitle="Scan or tap to pay from any UPI app — PhonePe, Google Pay, "
             "Paytm, BHIM, and more.",
)

# Pre-fill from book.py / track.py via session state
default_token = st.session_state.get("pay_token", "")
default_phone = st.session_state.get("pay_phone", "")

with st.form("pay_lookup"):
    c1, c2 = st.columns(2)
    token = c1.text_input("Token", value=default_token,
                          placeholder="C2S-XXXX", max_chars=20)
    phone = c2.text_input("Mobile number", value=default_phone,
                          placeholder="10-digit mobile", max_chars=10)
    look_up = st.form_submit_button("Look up booking →", type="primary",
                                    use_container_width=True)

if not (look_up or (default_token and default_phone)):
    st.info("Enter your token and the mobile number you used at booking.")
    st.stop()

booking = get_booking_by_token(token, phone)
if not booking:
    st.error("No booking found with that token + mobile combination.")
    st.stop()

# Persist for back-navigation
st.session_state["pay_token"] = token
st.session_state["pay_phone"] = phone

amount_due = (booking["govt_fee"] or 0) + (booking["service_charge"] or 0)

# Already paid?
if booking["payment_status"] == "verified":
    st.success(
        f"This booking is already paid in full (₹{booking['amount_paid']})."
    )
    st.stop()

if booking["payment_status"] == "submitted":
    st.warning(
        "Your payment is awaiting verification by the shop owner. "
        f"You submitted UTR **{booking.get('payment_ref')}** for "
        f"₹{booking['amount_paid']}."
    )
    st.caption(
        "✅ UTR submitted. The shop owner typically verifies within 15 minutes."
    )
    st.stop()

# ── Show booking summary ─────────────────────────────────────────────────────
with st.container(border=True):
    s1, s2, s3 = st.columns(3)
    s1.markdown(
        f"<div class='c2s-cat'>Token</div>"
        f"<div style='font-size:1.3rem; font-weight:900; "
        f"letter-spacing:-0.03em; color:#0E120F;'>{booking['token']}</div>",
        unsafe_allow_html=True,
    )
    s2.markdown(
        f"<div class='c2s-cat'>Service</div>"
        f"<div style='font-weight:600; color:#0E120F;'>"
        f"{booking['service_name']}</div>",
        unsafe_allow_html=True,
    )
    s3.markdown(
        f"<div class='c2s-cat'>Amount due</div>"
        f"<div style='font-size:2rem; font-weight:900; letter-spacing:-0.03em; "
        f"color:#0E120F;'>₹{amount_due}</div>",
        unsafe_allow_html=True,
    )

# ── Check shop UPI is configured ────────────────────────────────────────────
shop = get_shop_config()
shop_vpa = (shop["upi_vpa"] or "").strip()
shop_payee_name = (shop["upi_payee_name"]
                   or shop["shop_name"] or "Click2Serve").strip()

if not is_valid_vpa(shop_vpa):
    st.error(
        "Online payment is not yet configured by the shop owner. "
        "Please pay in cash at the shop, or contact the owner for their UPI ID."
    )
    if shop["owner_phone"]:
        st.info(f"Shop owner: {shop['owner_phone']}")
    st.stop()

# ── Build UPI deep link + QR ────────────────────────────────────────────────
upi_uri = build_upi_uri(
    payee_vpa=shop_vpa,
    payee_name=shop_payee_name,
    amount=amount_due,
    note=f"Click2Serve {booking['token']}",
)

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.markdown(
    "<div class='c2s-cat'>Step 01 · Pay</div>"
    "<h3 style='margin:0 0 1rem;'>Scan or tap to pay.</h3>",
    unsafe_allow_html=True,
)

col_qr, col_actions = st.columns([1, 1.2])

with col_qr:
    svg = qr_svg(upi_uri, scale=6, dark="#0E120F")
    st.markdown(
        f"<div style='background:#FFFFFF; padding:1.2rem; "
        f"border:1px solid #1F2620; display:inline-block;'>{svg}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<div style='margin-top:0.6rem; font-size:0.86rem;'>"
        f"<span style='color:#5A6157;'>Pay to</span> "
        f"<b>{shop_payee_name}</b><br/>"
        f"<code style='font-size:0.86rem; color:#0E120F;'>{shop_vpa}</code>"
        f"</div>",
        unsafe_allow_html=True,
    )

with col_actions:
    st.markdown(
        f"""
        <a href="{upi_uri}" target="_blank"
           style="display:inline-block; background:#0E120F; color:#F1ECE0;
                  padding:0.85rem 1.4rem; font-weight:600; font-size:0.95rem;
                  text-decoration:none; border:1px solid #0E120F;">
            Open UPI app on this phone →
        </a>
        """,
        unsafe_allow_html=True,
    )
    st.caption(
        "On your phone, the **Open UPI app** button lets your default UPI app "
        "(PhonePe, GPay, Paytm…) take over. On a desktop, scan the QR with "
        "your phone instead."
    )
    with st.expander("How does this work?"):
        st.markdown(
            """
            1. Your UPI app opens with the shop's UPI ID and amount pre-filled.
            2. Approve the payment with your UPI PIN.
            3. Copy the **UTR** (12-digit reference) the app shows you.
            4. Paste it below and click **Submit payment proof**.
            """
        )

# ── Step 2: submit UTR ──────────────────────────────────────────────────────
st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.markdown(
    "<div class='c2s-cat'>Step 02 · Confirm</div>"
    "<h3 style='margin:0 0 1rem;'>Confirm your payment.</h3>",
    unsafe_allow_html=True,
)

with st.form("submit_utr"):
    utr = st.text_input(
        "UTR / Transaction reference",
        placeholder="e.g. 412345678901",
        max_chars=22,
        help=(
            "The 12-digit reference your UPI app shows after a successful "
            "payment. Tap and hold inside your UPI app's transaction details "
            "to copy it."
        ),
    )
    if utr.strip():
        # Show a copy-able preview of what was typed — st.code adds the
        # built-in copy-to-clipboard button in modern Streamlit.
        st.caption("Preview — tap the icon on the right to copy:")
        st.code(utr.strip(), language=None)

    submit = st.form_submit_button("Submit payment proof →",
                                   type="primary",
                                   use_container_width=True)

if submit:
    if not is_valid_utr(utr):
        st.error("Please enter a valid 10–22 character UTR (alphanumeric).")
        st.stop()

    submit_payment_proof(booking["id"], ref=utr, amount=amount_due, method="UPI")
    st.success(
        "✅ UTR submitted. The shop owner typically verifies within 15 minutes."
    )
    st.balloons()
    # Clear pre-fill so a refresh shows the awaiting-verification banner
    st.rerun()
