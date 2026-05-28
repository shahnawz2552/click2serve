"""WhatsApp notifications via the CallMeBot free API.

Why CallMeBot?
    Zero approval, no business KYC, just a free GET endpoint. Perfect for
    an MVP. The catch: each phone that wants to RECEIVE messages must first
    send "I allow callmebot to send me messages" to CallMeBot's WhatsApp
    number, after which CallMeBot issues an api_key tied to that phone.

    For a single-shop deployment, the most realistic use is:
      • Owner registers their own phone with CallMeBot once.
      • Their api_key goes in Streamlit secrets.
      • The shop owner receives status alerts; they forward important
        ones to customers manually via WhatsApp.

    For per-customer push notifications, swap this module for Twilio
    WhatsApp or the Meta WhatsApp Business API.

All callers MUST tolerate failure — see ``notify_status_change``.
"""
from __future__ import annotations

import logging
from typing import Final

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
