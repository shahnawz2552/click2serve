"""Owner settings — shop info + UPI payment configuration."""
from __future__ import annotations

import streamlit as st

from core.db import (
    count_bookings, delete_all_bookings, get_shop_config,
    update_shop_config,
)
from core.email_sender import (
    email_transport_label, is_brevo_api_configured, is_email_configured,
    is_smtp_configured, send_test_email,
)
from core.notifications import (
    is_api_key_configured, is_twilio_configured, is_twilio_sms_configured,
    send_sms_test, send_test_message, send_twilio_test,
)
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

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
with st.expander("Send a test WhatsApp to yourself (CallMeBot)"):
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


# ── Section 04 — Twilio WhatsApp (auto-send to customer) ──────────────────
st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.markdown(
    "<div class='c2s-cat'>Section 04</div>"
    "<h3 style='margin:0 0 0.5rem;'>Auto-send to customer (Twilio WhatsApp).</h3>"
    "<p style='color:#5A6157; margin:0 0 0.8rem;'>"
    "When enabled, every booking status change automatically sends a "
    "WhatsApp message to the customer via Twilio. The wa.me click-to-chat "
    "link on the Bookings page stays available as a fallback whenever this "
    "auto-send fails or is off."
    "</p>",
    unsafe_allow_html=True,
)

twilio_ready = is_twilio_configured()
if twilio_ready:
    st.success(
        "Twilio credentials are **configured** in `secrets.toml`. "
        "Auto-send is ready to enable."
    )
else:
    st.warning(
        "Twilio credentials are **not configured**. Add a `[twilio]` "
        "block to your Streamlit secrets to enable auto-send. "
        "Setup instructions in the expander below."
    )

twilio_default = bool(shop.get("twilio_enabled"))

with st.form("twilio_form"):
    twilio_enabled = st.checkbox(
        "Auto-send WhatsApp to customer on every status change",
        value=twilio_default,
        disabled=not twilio_ready,
        help=(
            "Requires a [twilio] block in secrets.toml with account_sid, "
            "auth_token, and from_number. The shop owner is billed for "
            "every message Twilio delivers (sandbox is free for tests)."
        ),
    )
    save_twilio = st.form_submit_button(
        "Save Twilio settings →",
        type="primary",
        use_container_width=True,
        disabled=not twilio_ready,
    )

if save_twilio:
    try:
        update_shop_config(twilio_enabled=bool(twilio_enabled))
        st.success(
            "Saved. "
            + ("Customers will now be auto-notified on every status change."
               if twilio_enabled
               else "Auto-send is now off. The wa.me click-to-chat link "
                    "on Bookings still works.")
        )
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not save Twilio settings: {exc}")

with st.expander("Send a test WhatsApp via Twilio"):
    st.caption(
        "Sends a single 'test message' via Twilio to the phone you enter. "
        "Bypasses the toggle above so you can verify Twilio is reachable "
        "BEFORE turning auto-send on. The recipient must have joined your "
        "Twilio sandbox (production accounts can send to anyone)."
    )
    twilio_test_phone = st.text_input(
        "Phone number to test (with country code)",
        value=_shop_val("owner_phone"),
        max_chars=15,
        key="twilio_test_phone",
        help="Include country code, e.g. +919876543210.",
    )
    if st.button(
        "Send test via Twilio",
        key="twilio_test_btn",
        use_container_width=True,
        disabled=not twilio_ready,
    ):
        ok, reason = send_twilio_test(phone=twilio_test_phone)
        if ok:
            st.success(reason)
        else:
            st.error(reason)

with st.expander("Twilio setup — step by step"):
    st.markdown(
        """
        1. **Create a free Twilio account** at https://www.twilio.com/try-twilio.
        2. **Activate the WhatsApp Sandbox**:
           Console → Messaging → Try it out → *Send a WhatsApp message*.
           Twilio gives you a sandbox phone number (default `+14155238886`)
           and a join code like `join silver-rocket`.
        3. **Each customer phone that should receive sandbox messages** must
           send `join silver-rocket` (your code) to that sandbox number via
           WhatsApp. Once activated, the phone can receive Twilio sandbox
           messages automatically — no further opt-in per message.
        4. **Add to your Streamlit secrets** (locally `.streamlit/secrets.toml`,
           in the cloud Settings → Secrets):

           ```toml
           [twilio]
           account_sid = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
           auth_token  = "your-32-char-auth-token"
           from_number = "+14155238886"   # sandbox or your approved number
           ```

        5. **Test** with the button above, then flip the **Auto-send**
           toggle on. Status changes will now reach customers automatically.

        ---

        **Graduating from sandbox to production**:
        - Apply for a WhatsApp Business sender via Twilio Console.
        - Get a phone number approved by Meta and a few message templates
          pre-approved (1–2 days of paperwork).
        - Replace `from_number` in secrets with your approved number.
        - Customer phones no longer need a join code, but free-form
          messages are limited to a 24-hour window after the customer
          messages you; outside that window, only approved templates can
          be sent.
        """
    )


# ── Section 05 — Razorpay roadmap (unchanged) ─────────────────────────────
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



# ── Section 05 — SMS (Twilio, India: requires DLT registration) ──────────
# Sits between the Twilio WhatsApp section (04) and email (05a) because
# SMS uses the same provider but a different sender / template.
st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.markdown(
    "<div class='c2s-cat'>Section 05</div>"
    "<h3 style='margin:0 0 0.5rem;'>Auto-send SMS to customer (Twilio).</h3>"
    "<p style='color:#5A6157; margin:0 0 0.8rem;'>"
    "When enabled, every new booking sends a short text message to the "
    "customer with their booking number and ETA. Works on any phone, "
    "no app required \u2014 the most reliable channel for Indian "
    "customers."
    "</p>"
    "<p style='color:#5A6157; margin:0 0 0.8rem; font-size:0.86rem;'>"
    "<b>India compliance note:</b> TRAI requires every commercial SMS "
    "to use a DLT-registered sender ID and a pre-approved template. "
    "Twilio handles the registration through their portal but it takes "
    "1\u20132 weeks. Until DLT clears, SMS to Indian numbers will fail "
    "with carrier-block errors that the booking page surfaces in the "
    "Twilio HTTP error message. The wa.me click-to-chat button on the "
    "success card always works as a fallback while DLT is pending."
    "</p>",
    unsafe_allow_html=True,
)

sms_ready = is_twilio_sms_configured()
if sms_ready:
    st.success(
        "Twilio SMS sender is **configured**. Auto-send is ready to enable."
    )
else:
    st.warning(
        "Twilio SMS is **not configured**. Add `from_number_sms` to your "
        "`[twilio]` secrets block (or rely on the existing `from_number` "
        "as a fallback for sandbox testing). Setup walkthrough below."
    )

sms_default = bool(shop.get("sms_enabled"))

with st.form("sms_form"):
    sms_enabled = st.checkbox(
        "Auto-send SMS to customer on every new booking",
        value=sms_default,
        disabled=not sms_ready,
        help=(
            "Each SMS costs Twilio's per-segment rate (~Rs. 0.30 in "
            "India for DLT-registered traffic). Disable this if you "
            "want to rely on email + WhatsApp only."
        ),
    )
    save_sms = st.form_submit_button(
        "Save SMS settings \u2192",
        type="primary",
        use_container_width=True,
        disabled=not sms_ready,
    )

if save_sms:
    try:
        update_shop_config(sms_enabled=bool(sms_enabled))
        st.success(
            "Saved. "
            + ("Customers will now be auto-notified by SMS on every new "
               "booking." if sms_enabled
               else "Auto-send SMS is now off.")
        )
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not save SMS settings: {exc}")

with st.expander("Send a test SMS"):
    st.caption(
        "Sends one test message to the number you enter. Bypasses the "
        "toggle so you can verify Twilio reachability before going live. "
        "For Indian numbers in production, the recipient must be DLT-"
        "compliant — for development, use a Twilio trial-verified number."
    )
    sms_test_phone = st.text_input(
        "Phone number to test (with country code)",
        value=_shop_val("owner_phone"),
        max_chars=15,
        key="sms_test_phone",
        help="Include country code, e.g. +919876543210.",
    )
    if st.button(
        "Send test SMS",
        key="sms_test_btn",
        use_container_width=True,
        disabled=not sms_ready,
    ):
        ok, reason = send_sms_test(phone=sms_test_phone)
        if ok:
            st.success(reason)
        else:
            st.error(reason)

with st.expander("SMS setup \u2014 step by step"):
    st.markdown(
        """
        **Step 1 \u2014 Activate SMS on your Twilio account.**

        You already have a Twilio account from the WhatsApp setup
        (Section 04). To enable SMS:

        1. Twilio Console \u2192 **Phone Numbers** \u2192 **Manage** \u2192
           **Buy a number**.
        2. Filter by **Capabilities = SMS** and pick a number. Trial
           accounts get a free US +1 number that works for testing
           but won't deliver to real Indian customers without DLT.
        3. Note the number Twilio assigns you (e.g. `+12025550199`).

        **Step 2 \u2014 Add the SMS sender to your secrets.**

        Edit your existing `[twilio]` block in Streamlit secrets:

        ```toml
        [twilio]
        account_sid     = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        auth_token      = "your-32-char-token"
        from_number     = "+14155238886"     # WhatsApp sandbox
        from_number_sms = "+12025550199"     # the SMS-capable number you bought
        ```

        Save \u2192 Streamlit auto-restarts \u2192 the green status pill
        in this section will switch to "configured".

        **Step 3 \u2014 (India only) Register for DLT.**

        TRAI requires every commercial SMS to Indian numbers to use a
        DLT-registered sender ID and a template that's been pre-approved
        by the recipient's carrier. Twilio runs the whole registration:

        1. Open Twilio's DLT registration portal:
           https://www.twilio.com/docs/sms/dlt-registration
        2. Follow their forms (entity registration, header registration,
           template registration). Total: 1\u20132 weeks.
        3. Once approved, set `from_number_sms` to the registered DLT
           sender ID and update the SMS template in
           `core/notifications.py` (`customer_booking_confirmation_sms_message`)
           to match the approved template wording exactly.

        Until DLT is approved, sending to Indian numbers returns errors
        like *Twilio code 30007: Carrier filtering blocked* \u2014 the
        booking page surfaces these in the success toast so the owner
        can see what's blocked.

        **Step 4 \u2014 Test with the button above.**

        Use a number you control (your own mobile). On a Twilio trial
        account, only verified-trial numbers can receive SMS \u2014 add
        your number at Twilio Console \u2192 Phone Numbers \u2192
        **Verified Caller IDs** first.

        ---

        **Troubleshooting common Twilio SMS errors:**

        - **21408** \u2014 Geo permissions blocking the destination.
          Twilio Console \u2192 Messaging \u2192 Settings \u2192
          Geo Permissions \u2192 enable India.
        - **30007** \u2014 Carrier filtering. India-specific; means DLT
          isn't registered or template doesn't match.
        - **21606** \u2014 The 'From' number isn't SMS-capable. Buy an
          SMS-capable number and put it in `from_number_sms`.
        - **21211 / 21614** \u2014 Recipient number invalid for SMS.
        """
    )


# ── Section 05a — Booking-confirmation email (SMTP) ─────────────────────
# Lets the owner configure SMTP credentials (server-side only, in
# Streamlit secrets) and run a test email before relying on it. When
# configured, every new booking emails the customer their booking
# number + service summary right after submit.
st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.markdown(
    "<div class='c2s-cat'>Section 05a</div>"
    "<h3 style='margin:0 0 0.5rem;'>Booking confirmation \u2014 email.</h3>"
    "<p style='color:#5A6157; margin:0 0 0.8rem;'>"
    "When configured, customers automatically receive their booking "
    "number and service summary by email immediately after submission. "
    "Combined with the WhatsApp confirmation, this gives every customer "
    "two independent copies of their booking number."
    "</p>",
    unsafe_allow_html=True,
)

email_ready = is_email_configured()
if email_ready:
    st.success(
        f"Email transport is **configured** ({email_transport_label()}). "
        f"Booking confirmation emails are being sent automatically."
    )
else:
    st.warning(
        "Email is **not configured**. Booking emails will be skipped "
        "until you add either a `[brevo_api]` (HTTP, recommended for "
        "Streamlit Cloud) or `[smtp]` block to your Streamlit secrets. "
        "Setup walkthrough below."
    )

with st.expander("Send a test email"):
    st.caption(
        "Sends a single 'this is a test' email to the address you enter. "
        "Useful for verifying SMTP is reachable before relying on it for "
        "real customers."
    )
    test_email_addr = st.text_input(
        "Email address to test",
        value="",
        placeholder="you@example.com",
        key="smtp_test_email",
        max_chars=120,
    )
    if st.button(
        "Send test email",
        key="smtp_test_btn",
        use_container_width=True,
        disabled=not email_ready,
    ):
        ok, reason = send_test_email(to_email=test_email_addr)
        if ok:
            st.success(reason)
        else:
            st.error(reason)

with st.expander("Recommended: Brevo HTTP API (no SMTP, no IP whitelist)"):
    st.markdown(
        """
        **Best path for Streamlit Cloud users.** Streamlit Cloud sends
        from rotating shared IPs, which Brevo's SMTP firewall blocks
        with `525 Unauthorized IP` errors. The HTTP API has no such
        restriction \u2014 same provider, same free 300/day quota, just
        a cleaner transport.

        **Step 1.** Go to https://app.brevo.com/settings/keys/api
        (note: `/keys/api`, NOT `/keys/smtp`) \u2014 this is a
        *different* tab from the SMTP credentials.

        **Step 2.** Click **Generate a new API key** \u2014 name it
        `Click2Serve-API`. The key starts with `xkeysib-...`.
        Copy it immediately (Brevo shows it only once).

        **Step 3.** In Streamlit Cloud secrets, paste this block.
        Remove or comment out any existing `[smtp]` block \u2014 if both
        are present, the HTTP API wins.

        ```toml
        [brevo_api]
        api_key    = "xkeysib-..."           # from /settings/keys/api
        from_email = "<your Brevo signup email>"
        from_name  = "Click2Serve"
        ```

        **Step 4.** Save \u2192 wait ~30s for Streamlit to restart \u2192
        the green status pill above changes to *Email transport is
        configured (Brevo HTTP API)*.

        **Step 5.** Click **Send a test email** above with your Brevo
        signup email \u2014 you should get the test in 2\u201310s.

        ---

        **Why not just whitelist Streamlit Cloud's IPs on Brevo?**
        Streamlit Cloud's outbound IP changes between deploys and
        sometimes mid-session. You'd be in a permanent whack-a-mole
        keeping the whitelist current. The HTTP API skips that
        entirely.
        """
    )

with st.expander("SMTP setup \u2014 step by step"):
    st.markdown(
        """
        **Step 1 \u2014 Pick an SMTP provider.**

        - **Gmail** is the simplest if your shop already has a Google
          account. Free, but you must generate an App Password (regular
          Google passwords are blocked from SMTP):
          https://myaccount.google.com/apppasswords
        - **Brevo** (formerly Sendinblue) is free up to 300 emails/day
          and gives proper SMTP credentials at
          https://app.brevo.com/settings/keys/smtp
        - **Mailgun**, **SendGrid**, or your own ISP also work \u2014 anything
          that speaks plain SMTP.

        **Step 2 \u2014 Add credentials to your Streamlit secrets.**

        For Streamlit Community Cloud: **Manage app \u2192 Settings \u2192 Secrets**.
        For local dev: `.streamlit/secrets.toml`.

        ```toml
        [smtp]
        host        = "smtp.gmail.com"
        port        = 587
        username    = "yourshop@gmail.com"
        password    = "<app-specific password>"   # NOT your Google password
        from_email  = "yourshop@gmail.com"
        from_name   = "Click2Serve Bharatpur"
        use_tls     = true
        ```

        **Step 3 \u2014 Verify with the test button above.**

        After saving the secrets, the app reboots automatically (~30s).
        Refresh this page, expand 'Send a test email', enter your own
        email, and click the button. You should receive the test in 5\u201310s.

        **Step 4 \u2014 You're done.**

        Every new booking now triggers an email automatically. Failures
        are logged but never block the booking itself \u2014 if the SMTP
        provider is down, the customer still gets their token on screen
        (and via WhatsApp if Twilio / wa.me are wired up).

        ---

        **Common errors:**
        - *Authentication failed* \u2014 wrong password. For Gmail, must be an
          App Password, not the account password.
        - *Connection refused* \u2014 wrong host or port. Gmail uses 587
          (TLS) or 465 (SSL). Set `port = 465` and the module switches
          to SMTPS automatically.
        - *Sender address rejected* \u2014 some providers (e.g. Mailgun)
          require `from_email` to be a verified domain.
        """
    )


# ── Section 06 — Local SEO & Google Maps (NEW) ───────────────────────────
st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.markdown(
    "<div class='c2s-cat'>Section 06</div>"
    "<h3 style='margin:0 0 0.5rem;'>Local SEO &amp; Google Maps.</h3>"
    "<p style='color:#5A6157; margin:0 0 0.8rem;'>"
    "Make your shop appear when customers search "
    "<i>'passport service near me'</i> on Google. The fields here power "
    "the embedded map on the Contact page and the schema.org "
    "<code>LocalBusiness</code> structured data we emit on every page "
    "(which is what unlocks the green <b>Book Now</b> button on your "
    "Google Business Profile)."
    "</p>",
    unsafe_allow_html=True,
)

with st.form("local_seo_form"):
    business_url = st.text_input(
        "Public app URL (your Streamlit Cloud URL)",
        value=_shop_val("business_url"),
        placeholder="https://click2serve.streamlit.app",
        help=(
            "The URL customers reach when they tap 'Book Now' on your "
            "Google listing. Add ?utm_source=google&utm_medium=gbp at the "
            "end so we can track inbound Maps traffic."
        ),
    )

    c_seo1, c_seo2 = st.columns(2)
    maps_url = c_seo1.text_input(
        "Google Maps share URL",
        value=_shop_val("maps_url"),
        placeholder="https://maps.app.goo.gl/...",
        help=(
            "Open your shop on Google Maps → tap 'Share' → 'Copy link'. "
            "Used for the 'Open in Google Maps' button on the Contact page."
        ),
    )
    place_id = c_seo2.text_input(
        "Google Place ID (optional)",
        value=_shop_val("place_id"),
        placeholder="ChIJ...",
        help=(
            "Lookup at https://developers.google.com/maps/documentation/"
            "places/web-service/place-id. Helps Google match this app to "
            "your business listing."
        ),
    )

    maps_embed_url = st.text_input(
        "Maps embed URL (iframe src)",
        value=_shop_val("maps_embed_url"),
        placeholder="https://www.google.com/maps/embed?pb=...",
        help=(
            "On Google Maps, click 'Share' → 'Embed a map' → 'Copy HTML' "
            "and paste only the <i>src=\"...\"</i> URL here."
        ),
    )

    c_lat, c_lng = st.columns(2)
    lat_str = c_lat.text_input(
        "Latitude (optional)",
        value=str(_shop_val("latitude") or ""),
        placeholder="27.2152",
    )
    lng_str = c_lng.text_input(
        "Longitude (optional)",
        value=str(_shop_val("longitude") or ""),
        placeholder="77.4977",
    )

    save_seo = st.form_submit_button(
        "Save SEO settings →",
        type="primary",
        use_container_width=True,
    )

if save_seo:
    update: dict = {
        "business_url": business_url.strip(),
        "maps_url": maps_url.strip(),
        "maps_embed_url": maps_embed_url.strip(),
        "place_id": place_id.strip(),
    }
    # Latitude/longitude are nullable — only persist when valid floats.
    for key, raw in (("latitude", lat_str), ("longitude", lng_str)):
        raw = raw.strip()
        if not raw:
            update[key] = None
            continue
        try:
            update[key] = float(raw)
        except ValueError:
            st.error(f"{key.title()} must be a number (e.g. 27.2152).")
            st.stop()
    try:
        update_shop_config(**update)
        st.success(
            "SEO settings saved. The Contact page map and the page-level "
            "structured data will refresh on next page load."
        )
        st.rerun()
    except Exception as exc:  # noqa: BLE001
        st.error(f"Could not save SEO settings: {exc}")

with st.expander("How to get listed on Google Maps with a Book Now button"):
    st.markdown(
        """
        **Step 1 — Claim or create your Google Business Profile** (free).

        1. Open https://business.google.com.
        2. Search for your shop name. If a listing exists, click *Claim*.
           Otherwise click *Add your business to Google* and pick the
           closest category — **"Public Service"** or
           **"Document Center"** are good fits for a paperwork shop.
        3. Enter your address, phone (the same number you saved in
           Section 01 above), and opening hours. Google will verify by
           postcard or video — usually 3–5 days.

        **Step 2 — Set the 'Appointment URL' on the listing.**

        1. In your Business Profile dashboard, go to *Edit profile* →
           *Contact* → *Appointment links*.
        2. Paste your Streamlit Cloud URL with a UTM tag, exactly:

           ```
           https://yourshop.streamlit.app/?utm_source=google&utm_medium=gbp
           ```

        This is what makes the green **Book Now** button appear on your
        listing in Google Maps and Google Search.

        **Step 3 — Confirm Google sees the structured data.**

        After Streamlit Cloud redeploys, paste your URL into Google's
        Rich Results Test:
        https://search.google.com/test/rich-results

        You should see *LocalBusiness* with your shop name and a
        *ReserveAction* entry. If anything is missing, fill it in
        Section 01 above (shop name, address, phone, hours) and re-save.

        **Step 4 — Fill the fields above so the Contact page shows a real map.**

        - **Google Maps share URL** → tap *Share* → *Copy link* on your
          listing. The Contact page's *Open in Google Maps* button will
          take customers straight to your real listing instead of a
          generic address search.
        - **Maps embed URL** → tap *Share* → *Embed a map* → copy only
          the `src="..."` URL from the iframe HTML. Pastes a real,
          interactive map of your exact shop into the Contact page.

        **What you'll see in 1–2 weeks:**

        - "Found you on Google!" banner appears for inbound visitors.
        - Customers search "passport service near me" → see your shop
          → tap *Book Now* → land directly on Click2Serve.
        - Inbound bookings get tagged with `utm_source=google` so you
          can tell Maps traffic from word-of-mouth in the Revenue page
          (future enhancement).
        """
    )



# Typed-confirmation gate: the owner must type DELETE ALL exactly. We
# also stash a 'reveal' flag in session state so the destructive button
# isn't even visible until the owner expands the section, and the form
# clears itself after every submit.
st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.markdown(
    "<div class='c2s-cat' style='color:#B91C1C;'>Section 07 \u00b7 Danger zone</div>"
    "<h3 style='margin:0 0 0.6rem; color:#B91C1C;'>Reset all bookings.</h3>"
    "<p style='color:#5A6157; margin:0 0 0.8rem;'>"
    "Permanently deletes <b>every booking</b> in the system along with their "
    "uploaded documents. Service catalog, shop config, and the owner "
    "account are NOT affected. Cannot be undone."
    "</p>",
    unsafe_allow_html=True,
)

current_count = count_bookings()
if current_count == 0:
    st.success("There are no bookings to delete.")
else:
    st.warning(
        f"You currently have **{current_count}** booking(s) on file. "
        f"Resetting will delete every single one."
    )

    # Two-stage UX: an expander hides the danger fields until the owner
    # actively opts in. Inside the expander, a form requires typing
    # 'DELETE ALL' before the submit button does anything.
    with st.expander("I understand, show me the reset controls"):
        with st.form("danger_zone_reset_all", clear_on_submit=True):
            st.error(
                "**This action is irreversible.** Type the phrase below "
                "exactly to confirm."
            )
            confirm = st.text_input(
                "Type `DELETE ALL` (uppercase, exactly) to enable the button",
                placeholder="DELETE ALL",
                key="danger_confirm_text",
            )
            do_reset = st.form_submit_button(
                f"Permanently delete all {current_count} booking(s)",
                use_container_width=True,
                type="primary",
                disabled=(confirm.strip() != "DELETE ALL"),
            )

        if do_reset and confirm.strip() == "DELETE ALL":
            try:
                removed = delete_all_bookings()
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not reset bookings: {exc}")
            else:
                st.success(
                    f"Done. Deleted {removed} booking(s) and any attached "
                    f"documents."
                )
                st.rerun()
