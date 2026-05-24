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
    "In Progress": "Your booking {token} is now being processed. — Click2Serve",
    "Ready":       "Your booking {token} is ready for pickup! — Click2Serve",
    "Delivered":   "Your booking {token} has been delivered. Thank you! — Click2Serve",
    "Cancelled":   ("Your booking {token} has been cancelled. "
                    "Contact the shop for details. — Click2Serve"),
}

_CALLMEBOT_URL: Final[str] = "https://api.callmebot.com/whatsapp.php"


def _api_key() -> str:
    cfg = st.secrets.get("callmebot", {}) if hasattr(st, "secrets") else {}
    return (cfg.get("api_key") or "").strip()


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


def notify_status_change(
    *, phone: str, token: str, status: str, timeout: float = 5.0,
) -> bool:
    """Fire a WhatsApp message when a booking status changes.

    Returns True if the request returned 2xx, False otherwise. NEVER raises —
    notification failure must not block the underlying status update.
    """
    template = _STATUS_TEMPLATES.get(status)
    if not template:
        return False  # statuses like "Pending" don't ping the customer

    api_key = _api_key()
    if not api_key:
        logger.info("CallMeBot api_key not configured — skipping notification.")
        return False

    message = template.format(token=token)
    params = {
        "phone": _normalize_phone(phone),
        "text": message,
        "apikey": api_key,
    }
    try:
        resp = requests.get(_CALLMEBOT_URL, params=params, timeout=timeout)
        ok = 200 <= resp.status_code < 300
        if not ok:
            logger.warning(
                "CallMeBot returned %s for token=%s status=%s",
                resp.status_code, token, status,
            )
        return ok
    except requests.RequestException as exc:
        logger.warning("CallMeBot request failed: %s", exc)
        return False
    except Exception as exc:  # last-resort safety
        logger.exception("Unexpected notification error: %s", exc)
        return False
