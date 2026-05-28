"""WhatsApp notifications — owner alerts (auto) + customer notifications.

Three notification channels are supported, in order of preference:

1. **Owner alert (auto, via CallMeBot)**
   When a booking changes status, fire a formatted alert to the OWNER's
   phone (the one tied to the api_key in secrets.toml). The message
   embeds the customer's name + phone for context.

2. **Customer auto-notify (auto, via Twilio WhatsApp)**
   When credentials are present in secrets.toml AND the toggle is on
   in Settings, fire a customer-facing message via Twilio's WhatsApp
   API. Works for any phone in production mode (no opt-in required
   for approved templates), or for phones that have joined the Twilio
   sandbox in test mode.

3. **Customer click-to-chat (one-tap manual fallback)**
   If Twilio isn't configured, or fails, the bookings page surfaces a
   ``https://wa.me/<phone>?text=<message>`` link. Owner taps once,
   WhatsApp opens with the message pre-filled, they hit Send. Zero
   cost, works for any phone, no API approvals.

All callers MUST tolerate failure — see ``notify_status_change``.
"""
from __future__ import annotations

import logging
from typing import Final
from urllib.parse import quote

import requests
import streamlit as st

logger = logging.getLogger(__name__)

_STATUS_TEMPLATES: Final[dict[str, str]] = {
    "In Progress": (
        "🔧 *{token}* — {customer_name} ({customer_phone})\n"
        "Status: IN PROGRESS\n"
        "— Click2Serve"
    ),
    "Ready": (
        "✅ *{token}* — {customer_name} ({customer_phone})\n"
        "Status: READY for pickup\n"
        "— Click2Serve"
    ),
    "Delivered": (
        "📦 *{token}* — {customer_name} ({customer_phone})\n"
        "Status: DELIVERED\n"
        "— Click2Serve"
    ),
    "Cancelled": (
        "❌ *{token}* — {customer_name} ({customer_phone})\n"
        "Status: CANCELLED\n"
        "— Click2Serve"
    ),
}


# Customer-facing templates — used to build the wa.me click-to-chat link.
_CUSTOMER_TEMPLATES: Final[dict[str, str]] = {
    "Pending": (
        "Hi {customer_name}, we've received your booking *{token}* "
        "({service_name}). We'll send another update once it moves to "
        "'in progress'. — {shop_name}"
    ),
    "In Progress": (
        "Hi {customer_name}, your booking *{token}* ({service_name}) is "
        "now *in progress*. We'll let you know when it's ready. "
        "— {shop_name}"
    ),
    "Ready": (
        "Hi {customer_name}, your booking *{token}* ({service_name}) is "
        "*ready for pickup*! Please visit the shop during opening hours "
        "to collect it. — {shop_name}"
    ),
    "Delivered": (
        "Hi {customer_name}, your booking *{token}* ({service_name}) has "
        "been *delivered*. Thank you for choosing us! — {shop_name}"
    ),
    "Cancelled": (
        "Hi {customer_name}, your booking *{token}* ({service_name}) has "
        "been *cancelled*. Please contact us if you have any questions. "
        "— {shop_name}"
    ),
}

_CALLMEBOT_URL: Final[str] = "https://api.callmebot.com/whatsapp.php"


def _api_key() -> str:
    cfg = st.secrets.get("callmebot", {}) if hasattr(st, "secrets") else {}
    return (cfg.get("api_key") or "").strip()


def is_api_key_configured() -> bool:
    """Public helper for the settings page: do we have a CallMeBot key?"""
    return bool(_api_key())


def _whatsapp_enabled() -> bool:
    """Return True if the shop owner has notifications turned on.

    Reads ``whatsapp_enabled`` from ``shop_config``. Defaults to True so
    existing deployments keep their previous behaviour (notifications were
    always on before the toggle existed). If the DB lookup fails for any
    reason (no connection, missing column on a stale schema), we also
    default to True — fail open rather than silently swallow alerts.
    """
    try:
        # Lazy import to avoid a circular import at module load time.
        from core.db import get_shop_config

        cfg = get_shop_config() or {}
        val = cfg.get("whatsapp_enabled")
        return True if val is None else bool(val)
    except Exception as exc:  # noqa: BLE001
        logger.debug(
            "Could not read whatsapp_enabled flag, defaulting to True: %s", exc,
        )
        return True


def _normalize_phone(phone: str) -> str:
    """Return phone in international E.164-ish form for CallMeBot.

    CallMeBot expects '+<country><number>'. We assume Indian customers if
    a 10-digit number starting with 6/7/8/9 is given.
    """
    p = (phone or "").strip().replace(" ", "").replace("-", "")
    if p.startswith("+"):
        p = p[1:]
    if len(p) == 10 and p[0] in "6789":
        p = "91" + p
    return "+" + p


def _owner_phone() -> str:
    """Read the shop owner's phone from config.

    This is the phone where status alerts are delivered. CallMeBot's free
    API only sends to phones that have activated themselves, so for a
    multi-customer shop it makes no sense to target ``customer_phone`` —
    we ping the owner and they relay to the customer manually.
    """
    try:
        from core.db import get_shop_config

        cfg = get_shop_config() or {}
        return (cfg.get("owner_phone") or "").strip()
    except Exception as exc:  # noqa: BLE001
        logger.debug("Could not read owner_phone: %s", exc)
        return ""


def notify_status_change(
    *,
    token: str,
    status: str,
    customer_name: str = "",
    customer_phone: str = "",
    timeout: float = 5.0,
) -> bool:
    """Send a WhatsApp alert to the SHOP OWNER when a booking status changes.

    The message includes the customer's name + phone so the owner can copy
    them and forward the update to the customer via their own WhatsApp.

    Why not message the customer directly? CallMeBot's free API requires
    each receiving phone to have sent the activation message — so it can
    only deliver to phones the shop has explicitly onboarded. For
    real customer-facing push, swap this module for Twilio WhatsApp or
    the Meta WhatsApp Business API.

    Returns True on a successful 2xx from CallMeBot. NEVER raises —
    notification failure must not block the underlying status update.
    """
    template = _STATUS_TEMPLATES.get(status)
    if not template:
        return False  # statuses like "Pending" don't ping the owner

    if not _whatsapp_enabled():
        logger.info(
            "WhatsApp notifications disabled in shop settings — "
            "skipping alert for token=%s status=%s",
            token, status,
        )
        return False

    if not _api_key():
        logger.info("CallMeBot api_key not configured — skipping notification.")
        return False

    target = _owner_phone()
    if not target:
        logger.info(
            "owner_phone not set in Settings — cannot deliver WhatsApp "
            "alert for token=%s.",
            token,
        )
        return False

    message = template.format(
        token=token,
        customer_name=(customer_name or "—").strip() or "—",
        customer_phone=(customer_phone or "—").strip() or "—",
    )
    return _send_whatsapp(phone=target, message=message, timeout=timeout)


def send_test_message(*, phone: str, timeout: float = 5.0) -> tuple[bool, str]:
    """Send a single 'this is a test' message — used by the Settings page.

    Returns (ok, human_readable_reason). Bypasses the whatsapp_enabled
    toggle so the owner can verify their CallMeBot setup before turning
    notifications on.
    """
    if not _api_key():
        return False, (
            "CallMeBot api_key is not configured. Add it under "
            "[callmebot] in .streamlit/secrets.toml."
        )
    if not (phone or "").strip():
        return False, "Please enter a phone number to test."

    ok = _send_whatsapp(
        phone=phone,
        message=(
            "Click2Serve — test message. If you got this, your WhatsApp "
            "notification setup is working."
        ),
        timeout=timeout,
    )
    if ok:
        return True, f"Test message sent to {_normalize_phone(phone)}."
    return False, (
        "CallMeBot rejected the request. Most common cause: this phone "
        "has not yet sent the activation message to CallMeBot's WhatsApp "
        "number. See https://www.callmebot.com/blog/free-api-whatsapp-messages/"
    )


def _send_whatsapp(*, phone: str, message: str, timeout: float) -> bool:
    """Internal HTTP wrapper. Returns True on 2xx, False otherwise."""
    params = {
        "phone": _normalize_phone(phone),
        "text": message,
        "apikey": _api_key(),
    }
    try:
        resp = requests.get(_CALLMEBOT_URL, params=params, timeout=timeout)
        ok = 200 <= resp.status_code < 300
        if not ok:
            logger.warning(
                "CallMeBot returned %s for phone=%s",
                resp.status_code, _normalize_phone(phone),
            )
        return ok
    except requests.RequestException as exc:
        logger.warning("CallMeBot request failed: %s", exc)
        return False
    except Exception as exc:  # last-resort safety
        logger.exception("Unexpected notification error: %s", exc)
        return False


# ──────────────────────────────────────────────────────────────────────────
# Customer click-to-chat link generation (no API, no opt-in needed)
# ──────────────────────────────────────────────────────────────────────────
def _shop_name() -> str:
    """Read shop_name from config for use in customer-facing messages."""
    try:
        from core.db import get_shop_config

        cfg = get_shop_config() or {}
        return (cfg.get("shop_name") or "Click2Serve").strip() or "Click2Serve"
    except Exception:  # noqa: BLE001
        return "Click2Serve"


def customer_status_message(
    *,
    status: str,
    token: str,
    customer_name: str,
    service_name: str,
    shop_name: str | None = None,
) -> str:
    """Build the customer-facing message text for a given status.

    Always returns a usable string — falls back to a generic
    "status updated" line if the status isn't in the customer template
    map. Uses just the customer's first name to keep the greeting
    natural ("Hi Rajesh," instead of "Hi Rajesh Kumar Sharma,").
    """
    template = _CUSTOMER_TEMPLATES.get(status) or (
        "Hi {customer_name}, your booking *{token}* ({service_name}) "
        "status is now *{status}*. — {shop_name}"
    )
    first_name = (customer_name or "").strip().split()[:1]
    return template.format(
        token=(token or "").strip() or "—",
        customer_name=(first_name[0] if first_name else "there"),
        service_name=(service_name or "your service").strip() or "your service",
        shop_name=(shop_name or _shop_name()),
        status=status,
    )


def customer_whatsapp_chat_url(*, customer_phone: str, message: str) -> str:
    """Return a wa.me deep-link that opens WhatsApp with a pre-filled
    message ready to send to the given customer.

    Returns an empty string when ``customer_phone`` is empty/invalid;
    callers should hide their button in that case. The number is
    normalized to international form WITHOUT the leading '+' (which is
    what wa.me expects), so '9876543210' becomes '919876543210'.
    """
    if not (customer_phone or "").strip():
        return ""
    # _normalize_phone returns "+919876543210" — strip the leading "+"
    # because wa.me expects the digits only.
    norm = _normalize_phone(customer_phone).lstrip("+")
    if not norm or not norm.isdigit():
        return ""
    return f"https://wa.me/{norm}?text={quote(message)}"



# ──────────────────────────────────────────────────────────────────────────
# Twilio WhatsApp — automatic customer push (opt-in via secrets + Settings)
# ──────────────────────────────────────────────────────────────────────────
# Setup (one-time):
#   1. Create a free Twilio account at https://www.twilio.com/try-twilio
#   2. Activate the WhatsApp Sandbox at
#      Console → Messaging → Try it out → Send a WhatsApp message.
#      You'll get a sandbox number (default +14155238886) and a join code.
#   3. On every customer phone that should receive sandbox messages, send
#      "join <your-code>" via WhatsApp to that number. Once activated, the
#      phone can receive Twilio sandbox messages automatically.
#   4. Add to .streamlit/secrets.toml (or Streamlit Cloud → Secrets):
#          [twilio]
#          account_sid = "ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
#          auth_token  = "your-32-char-token"
#          from_number = "+14155238886"   # sandbox or your approved number
#   5. Toggle on "Auto-send to customer via Twilio" in Settings → Section 03.
#
# Production (graduating from sandbox):
#   • Apply for a WhatsApp Business sender via Twilio Console.
#   • Get a phone number approved by Meta and a few message templates
#     pre-approved.
#   • Replace ``from_number`` with your approved number.
#   • Customer phones no longer need a join code, but free-form messages
#     are limited to a 24-hour window after the customer messages you;
#     outside that window, only approved templates can be sent.
_TWILIO_API: Final = "https://api.twilio.com/2010-04-01/Accounts/{sid}/Messages.json"


def _twilio_secrets() -> dict:
    """Return the [twilio] section of secrets, or empty dict if absent."""
    if not hasattr(st, "secrets"):
        return {}
    try:
        return dict(st.secrets.get("twilio", {}) or {})
    except Exception:  # noqa: BLE001
        return {}


def is_twilio_configured() -> bool:
    """Return True iff all three required Twilio credentials are present."""
    s = _twilio_secrets()
    return bool(
        (s.get("account_sid") or "").strip()
        and (s.get("auth_token") or "").strip()
        and (s.get("from_number") or "").strip()
    )


def _twilio_enabled() -> bool:
    """Read the per-shop Twilio toggle from shop_config.

    Defaults to False so existing deployments don't start sending paid
    messages without the owner explicitly turning it on.
    """
    try:
        from core.db import get_shop_config

        cfg = get_shop_config() or {}
        return bool(cfg.get("twilio_enabled"))
    except Exception:  # noqa: BLE001
        return False


def _twilio_to(phone: str) -> str:
    """Format a phone number for Twilio's ``To=whatsapp:+...`` parameter."""
    norm = _normalize_phone(phone)  # already includes leading "+"
    if not norm:
        return ""
    return f"whatsapp:{norm}"


def _twilio_from(raw: str) -> str:
    """Format the configured ``from_number`` for Twilio's ``From`` field."""
    raw = (raw or "").strip()
    if not raw:
        return ""
    if raw.startswith("whatsapp:"):
        return raw
    if not raw.startswith("+"):
        raw = "+" + raw
    return f"whatsapp:{raw}"


def _send_via_twilio(
    *, to_phone: str, message: str, timeout: float = 8.0,
) -> tuple[bool, str]:
    """POST a single WhatsApp message to Twilio's Messages endpoint.

    Returns ``(ok, reason)``. Never raises — always returns a string the
    UI can display.
    """
    s = _twilio_secrets()
    sid = (s.get("account_sid") or "").strip()
    token = (s.get("auth_token") or "").strip()
    from_num = (s.get("from_number") or "").strip()
    if not (sid and token and from_num):
        return False, "Twilio credentials not configured in secrets.toml"

    to = _twilio_to(to_phone)
    if not to:
        return False, "Invalid recipient phone number"

    data = {
        "From": _twilio_from(from_num),
        "To": to,
        "Body": message,
    }
    try:
        resp = requests.post(
            _TWILIO_API.format(sid=sid),
            data=data,
            auth=(sid, token),
            timeout=timeout,
        )
    except requests.RequestException as exc:
        logger.warning("Twilio request failed: %s", exc)
        return False, f"Network error contacting Twilio: {exc}"
    except Exception as exc:  # last-resort safety
        logger.exception("Unexpected Twilio error: %s", exc)
        return False, f"Unexpected error: {exc}"

    if 200 <= resp.status_code < 300:
        return True, f"Sent to {to_phone}"

    # Surface Twilio's own error message when possible — it's usually
    # actionable (e.g. "Channel not found" = wrong from_number, or the
    # sandbox has expired).
    try:
        err = resp.json()
        twilio_msg = err.get("message") or err.get("more_info") or "unknown"
        twilio_code = err.get("code")
    except Exception:  # noqa: BLE001
        twilio_msg = (resp.text or "")[:200] or "unknown error"
        twilio_code = None

    code_str = f" (Twilio code {twilio_code})" if twilio_code else ""
    logger.warning(
        "Twilio %s for %s: %s%s",
        resp.status_code, to_phone, twilio_msg, code_str,
    )
    return False, f"Twilio HTTP {resp.status_code}{code_str}: {twilio_msg}"


def notify_customer_twilio(
    *,
    customer_phone: str,
    status: str,
    token: str,
    customer_name: str = "",
    service_name: str = "",
) -> tuple[bool, str]:
    """Try to push a customer WhatsApp via Twilio. Always safe to call.

    Short-circuits and returns ``(False, reason)`` when:
      - the toggle is off, or
      - credentials aren't in secrets.toml, or
      - customer_phone is empty.
    Callers should always also surface the wa.me click-to-chat link as
    a fallback regardless of what this returns.
    """
    if not _twilio_enabled():
        return False, "Twilio auto-send is disabled in Settings"
    if not is_twilio_configured():
        return False, "Twilio credentials not configured in secrets.toml"
    if not (customer_phone or "").strip():
        return False, "Customer has no phone on file"

    msg = customer_status_message(
        status=status, token=token,
        customer_name=customer_name, service_name=service_name,
    )
    return _send_via_twilio(to_phone=customer_phone, message=msg)


def send_twilio_test(*, phone: str) -> tuple[bool, str]:
    """Send a single 'test' message via Twilio. Used by Settings to let
    the owner verify their setup without touching a real booking.

    Bypasses the ``twilio_enabled`` toggle — credentials alone are enough
    to send the test, so the owner can confirm Twilio is reachable
    BEFORE turning auto-send on.
    """
    if not is_twilio_configured():
        return False, (
            "Twilio credentials are not configured. Add `[twilio]` block "
            "with account_sid, auth_token, and from_number to "
            ".streamlit/secrets.toml (or Streamlit Cloud Secrets)."
        )
    if not (phone or "").strip():
        return False, "Please enter a phone number to test."

    return _send_via_twilio(
        to_phone=phone,
        message=(
            "Click2Serve test message via Twilio WhatsApp. If you got this, "
            "your Twilio setup is working — you can now turn on auto-send "
            "in Settings."
        ),
    )
