"""Owner settings — shop info + UPI payment configuration."""
from __future__ import annotations

import streamlit as st

from core.db import get_shop_config, update_shop_config
from core.notifications import is_api_key_configured, send_test_message
from core.payments import is_valid_vpa
from core.styles import inject_global_css, section_header

inject_global_css()

if not st.session_state.get("logged_in"):
    st.warning("Please sign in to access settings.")
    st.page_link("pages/login.py", label="Owner login →",
                 use_container_width=True)
    st.stop()

section_header(
    eyebrow="Owner · Settings",
    title="Shop &amp; payment settings.",
    subtitle="Configure your shop info and the UPI ID that customers will pay to.",
)

# ── Load current shop config (defensive — never assume a key exists) ────────
# Older shop_config rows can be missing freshly-added columns. Treat the row
# as a sparse dict and pull values via .get(...) so a missing column never
# crashes the page mid-form (which would also swallow the submit button and
# trigger Streamlit's "missing submit button" error).
shop = get_shop_config() or {}


def _shop_val(key: str, default: str = "") -> str:
    """Read a string field from shop config, treating None as empty."""
    return (shop.get(key) or default) or ""


st.markdown(
    "<div class='c2s-cat'>Section 01</div>"
    "<h3 style='margin:0 0 1rem;'>Shop information.</h3>",
    unsafe_allow_html=True,
)
with st.form("shop_info"):
    c1, c2 = st.columns(2)
    shop_name = c1.text_input(
        "Shop name",
        value=_shop_val("shop_name", "Click2Serve"),
    )
    owner_name = c2.text_input(
        "Owner name",
        value=_shop_val("owner_name"),
    )

    c3, c4 = st.columns(2)
    owner_phone = c3.text_input(
        "Contact number",
        value=_shop_val("owner_phone"),
        placeholder="10-digit mobile",
    )
    opening_hours = c4.text_input(
        "Opening hours",
        value=_shop_val("opening_hours"),
        placeholder="e.g. 9:00 AM – 9:00 PM",
    )

    address = st.text_area(
        "Shop address",
        value=_shop_val("address"),
        height=80,
        placeholder="Full address shown to customers on their receipt.",
    )

    save_info = st.form_submit_button(
        "Save shop info →",
        type="primary",
        use_container_width=True,
    )

if save_info:
    try:
        update_shop_config(
            shop_name=shop_name, owner_name=owner_name,
            owner_phone=owner_phone, opening_hours=opening_hours,
            address=address,
        )
        st.success("Shop information updated.")
        st.rerun()
    except Exception as exc:  # noqa: BLE001 — surface DB errors to the user
        st.error(f"Could not save shop info: {exc}")

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.markdown(
    "<div class='c2s-cat'>Section 02</div>"
    "<h3 style='margin:0 0 0.5rem;'>Online payments — UPI.</h3>"
    "<p style='color:#5A6157; margin:0 0 1rem;'>"
    "Customers will scan a QR code that pays your UPI ID directly. "
    "After they pay they paste the UTR back into the app for you to verify."
    "</p>",
    unsafe_allow_html=True,
)

current_vpa = _shop_val("upi_vpa")
current_payee = _shop_val("upi_payee_name") or _shop_val("shop_name")

if current_vpa and is_valid_vpa(current_vpa):
    st.success(
        f"Online payments are **enabled**. Customers will pay to `{current_vpa}`."
    )
else:
    st.info(
        "Online payments are **not configured yet**. "
        "Add your UPI ID below to enable the customer pay page."
    )

with st.form("upi_form"):
    upi_vpa = st.text_input(
        "UPI ID (VPA)",
        value=current_vpa,
        placeholder="e.g. yourname@okaxis  ·  shop@upi  ·  9876543210@ybl",
        help=(
            "Find your UPI ID inside PhonePe / GPay / Paytm under 'My UPI' "
            "or 'Bank Account → Manage UPI ID'."
        ),
    )
    upi_payee_name = st.text_input(
        "Payee name (shown to customer)",
        value=current_payee,
        placeholder="e.g. Click2Serve Bharatpur",
    )
    save_upi = st.form_submit_button(
        "Save UPI settings →",
        type="primary",
        use_container_width=True,
    )

if save_upi:
    if upi_vpa and not is_valid_vpa(upi_vpa):
        st.error(
            "That doesn't look like a valid UPI ID. "
            "It must be in the format `name@bank`, e.g. `yourname@okaxis`."
        )
    else:
        try:
            update_shop_config(upi_vpa=upi_vpa, upi_payee_name=upi_payee_name)
            st.success("UPI settings saved. The customer pay page is now live.")
            st.rerun()
        except Exception as exc:  # noqa: BLE001
            st.error(f"Could not save UPI settings: {exc}")

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.markdown(
    "<div class='c2s-cat'>Section 03</div>"
    "<h3 style='margin:0 0 0.5rem;'>Customer notifications — WhatsApp.</h3>"
    "<p style='color:#5A6157; margin:0 0 0.6rem;'>"
    "Notifications work in <b>two complementary ways</b>:"
    "</p>"
    "<ol style='color:#5A6157; margin:0 0 1rem; padding-left:1.2rem;'>"
    "<li><b>Owner alert (auto):</b> when a booking changes status, you "
    "receive a WhatsApp ping on the contact number above. Powered by "
    "the free CallMeBot API — requires the api_key in your Streamlit "
    "secrets and a one-time activation of <i>your</i> phone with "
    "CallMeBot.</li>"
    "<li><b>Customer notify (one tap):</b> on the Bookings page, every "
    "open booking shows a <b>Send WhatsApp to customer</b> button. "
    "Tap it — WhatsApp opens on your device with a properly composed "
    "message pre-filled, and you press Send. Zero cost, works for any "
    "customer phone, no API approvals.</li>"
    "</ol>"
    "<p style='color:#5A6157; font-size:0.86rem; margin:0 0 1rem;'>"
    "<i>Want truly automatic customer push?</i> Swap CallMeBot for "
    "Twilio WhatsApp or Meta WhatsApp Business in "
    "<code>core/notifications.py</code>. Both require business KYC + "
    "template approvals; the click-to-chat flow above is the practical "
    "MVP path."
    "</p>",
    unsafe_allow_html=True,
)

# Status indicator: is the CallMeBot api_key configured?
api_key_ok = is_api_key_configured()
owner_phone_set = bool(_shop_val("owner_phone"))

if api_key_ok and owner_phone_set:
    st.success(
        f"Notifications will be delivered to **{_shop_val('owner_phone')}**."
    )
elif not api_key_ok:
    st.warning(
        "CallMeBot API key is **not configured**. Even if you enable the "
        "toggle below, no messages will go out until you add "
        "`[callmebot]\\napi_key = \"...\"` to your Streamlit secrets. "
        "Get a free key at "
        "https://www.callmebot.com/blog/free-api-whatsapp-messages/"
    )
elif not owner_phone_set:
    st.warning(
        "**Contact number** in Section 01 above is empty. Notifications "
        "are delivered to that number — please save a phone there first."
    )

# Default the toggle to True (matches old always-on behaviour) when the
# field is missing from a stale shop_config row.
notif_default = shop.get("whatsapp_enabled")
if notif_default is None:
    notif_default = True

with st.form("notifications_form"):
    whatsapp_enabled = st.checkbox(
        "Send WhatsApp notifications to the shop owner on status changes",
        value=bool(notif_default),
        help=(
            "Disable this if you'd rather track everything from the "
            "Bookings queue. Status changes still log internally; only "
            "the outbound WhatsApp call to CallMeBot is suppressed."
        ),
    )
    save_notif = st.form_submit_button(
        "Save notification settings →",
        type="primary",
        use_container_width=True,
    )

if save_notif:
    try:
        update_shop_config(whatsapp_enabled=bool(whatsapp_enabled))
        st.success(
            "Notification settings saved. "
            + ("You'll get a WhatsApp ping when bookings change status."
               if whatsapp_enabled
               else "Outbound WhatsApp alerts are now off.")
        )
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not save notification settings: {exc}")

# Test-message helper — bypasses the toggle so you can verify your
# CallMeBot setup before flipping the switch on.
with st.expander("Send a test message"):
    st.caption(
        "Sends a single 'this is a test' message to the number you enter, "
        "ignoring the toggle above. Useful for verifying that the receiving "
        "phone has activated CallMeBot."
    )
    test_phone = st.text_input(
        "Phone number to test",
        value=_shop_val("owner_phone"),
        max_chars=15,
        key="notif_test_phone",
    )
    if st.button(
        "Send test WhatsApp message",
        key="send_test_btn",
        use_container_width=True,
        disabled=not api_key_ok,
    ):
        ok, reason = send_test_message(phone=test_phone)
        if ok:
            st.success(reason)
        else:
            st.error(reason)

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
with st.expander("Want auto-reconciled payments? (Razorpay roadmap)"):
    st.markdown(
        """
        The current UPI flow needs you to confirm each UTR manually in your
        UPI app. For fully automatic reconciliation:

        1. Sign up at https://razorpay.com (free, requires business KYC).
        2. Generate API keys in Dashboard → Settings → API Keys.
        3. Add them to `.streamlit/secrets.toml`:

           ```toml
           [razorpay]
           key_id = "rzp_test_xxxxxxxxxxxxxx"
           key_secret = "your-secret"
           ```

        4. The repo's roadmap includes a Razorpay Payment Links integration
           that drops in here without changing the data model.
        """
    )
