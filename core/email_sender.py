"""Email sending — Brevo HTTP API (preferred) or SMTP (fallback).

Used by Click2Serve to email the customer their booking token + summary
right after a booking is created. Configurable through Streamlit secrets,
and graceful when not configured — pages call ``send_booking_email`` and
get back a ``(ok, reason)`` tuple they can fold into their success toast.

Two transports
--------------

1. **Brevo HTTP API (preferred for Brevo deployments)**
   No SMTP authentication, no IP whitelist, no port-587-vs-465 dance —
   just an HTTPS POST with a Bearer-style ``api-key`` header. Bypasses
   the ``525 Unauthorized IP address`` block that hits SMTP from
   shared-IP hosts like Streamlit Cloud.

   Configure with::

       [brevo_api]
       api_key    = "xkeysib-..."        # from /settings/keys/api
       from_email = "<your Brevo signup email or a verified sender>"
       from_name  = "Click2Serve"

2. **SMTP (works for Gmail / Resend / Brevo SMTP / Mailgun / SendGrid /
   custom servers)**
   Plain ``smtplib`` over STARTTLS or implicit-TLS. Authentication
   varies by provider — for Gmail you need an App Password, for
   Resend you literally use the string ``"resend"`` as username, etc.

   Configure with::

       [smtp]
       host        = "smtp-relay.brevo.com"   # or smtp.gmail.com / smtp.resend.com / ...
       port        = 587                      # or 465 for implicit TLS
       username    = "<provider-specific>"
       password    = "<provider-specific>"
       from_email  = "yourshop@..."
       from_name   = "Click2Serve"
       use_tls     = true

Selection rule
--------------

If ``[brevo_api]`` is configured AND has a non-empty ``api_key``, we use
HTTP and ignore SMTP. Otherwise we fall back to SMTP. Pages don't need
to know which transport ran — the public functions
``send_booking_email`` and ``send_test_email`` route automatically.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any

import requests
import streamlit as st

logger = logging.getLogger(__name__)


# ──────────────────────────────────────────────────────────────────────────
# Secret loaders + transport selection
# ──────────────────────────────────────────────────────────────────────────
_BREVO_API_URL = "https://api.brevo.com/v3/smtp/email"


def _smtp_secrets() -> dict[str, Any]:
    """Return the [smtp] section of secrets, or empty dict if absent."""
    if not hasattr(st, "secrets"):
        return {}
    try:
        return dict(st.secrets.get("smtp", {}) or {})
    except Exception:  # noqa: BLE001
        return {}


def _brevo_api_secrets() -> dict[str, Any]:
    """Return the [brevo_api] section of secrets, or empty dict if absent."""
    if not hasattr(st, "secrets"):
        return {}
    try:
        return dict(st.secrets.get("brevo_api", {}) or {})
    except Exception:  # noqa: BLE001
        return {}


def is_brevo_api_configured() -> bool:
    """True iff [brevo_api] is set with the required fields."""
    s = _brevo_api_secrets()
    return bool(
        (s.get("api_key") or "").strip()
        and (s.get("from_email") or "").strip()
    )


def is_smtp_configured() -> bool:
    """True iff [smtp] has the four required fields."""
    s = _smtp_secrets()
    return bool(
        (s.get("host") or "").strip()
        and (s.get("username") or "").strip()
        and (s.get("password") or "").strip()
        and (s.get("from_email") or "").strip()
    )


def is_email_configured() -> bool:
    """Return True iff EITHER transport is configured.

    Used by the Settings page to show the green/yellow status pill.
    """
    return is_brevo_api_configured() or is_smtp_configured()


def email_transport_label() -> str:
    """Return a short human label for the active email transport.

    Used by the Settings page so the owner can confirm at a glance
    which provider is actually doing the sending.
    """
    if is_brevo_api_configured():
        return "Brevo HTTP API"
    if is_smtp_configured():
        host = (_smtp_secrets().get("host") or "").lower()
        if "brevo" in host or "sendinblue" in host:
            return "Brevo SMTP"
        if "gmail" in host or "google" in host:
            return "Gmail SMTP"
        if "resend" in host:
            return "Resend SMTP"
        if "mailgun" in host:
            return "Mailgun SMTP"
        if "sendgrid" in host:
            return "SendGrid SMTP"
        return f"SMTP ({host})"
    return "not configured"


def _build_from_header() -> str:
    """Build the RFC-5322 `From` header for the active transport."""
    if is_brevo_api_configured():
        s = _brevo_api_secrets()
    else:
        s = _smtp_secrets()
    name = (s.get("from_name") or "Click2Serve").strip() or "Click2Serve"
    addr = (s.get("from_email") or s.get("username") or "").strip()
    return formataddr((name, addr))


def _auth_failure_message(host: str, raw_exc: Exception | None = None) -> str:
    """Return a provider-specific 'auth failed' message based on the host.

    The previous implementation always referenced Gmail App Passwords,
    which was misleading when the user was actually configured for
    Brevo / Mailgun / SendGrid / etc. This dispatches off the SMTP host
    so the customer-visible error matches what they actually need to
    fix.
    """
    h = (host or "").lower()
    detail = ""
    if raw_exc is not None:
        # Surface the underlying SMTP code/message so users (and us) can
        # debug from logs alone. Truncated to keep the toast readable.
        detail = f" (server said: {str(raw_exc)[:140]})"

    if "gmail" in h or "google" in h:
        return (
            "Gmail SMTP rejected the credentials. The password must be "
            "an App Password (16 chars, generated at "
            "https://myaccount.google.com/apppasswords) — your normal "
            "Google account password will NOT work."
            + detail
        )
    if "brevo" in h or "sendinblue" in h:
        return (
            "Brevo SMTP rejected the credentials. Check that:"
            "\n  1. `username` is the LOGIN value shown on "
            "https://app.brevo.com/settings/keys/smtp — for newer Brevo "
            "accounts this is a generated `xxxxxx@smtp-brevo.com` "
            "address, NOT your signup email."
            "\n  2. `password` is the SMTP key from that same SMTP tab "
            "(NOT the API key from the API Keys tab — those have "
            "different prefixes)."
            "\n  3. Your Brevo account's signup email is verified."
            "\n  4. If you're getting `525 Unauthorized IP`, the IP "
            "running this app isn't on Brevo's whitelist. Switch to the "
            "Brevo HTTP API (no IP restriction): add a [brevo_api] "
            "block to your secrets with `api_key` and `from_email`."
            + detail
        )
    if "mailgun" in h:
        return (
            "Mailgun rejected the credentials. `username` should be the "
            "SMTP login from your domain settings (postmaster@yourdomain "
            "or similar), and `password` should be the SMTP password "
            "from the Mailgun dashboard — NOT the API key."
            + detail
        )
    if "sendgrid" in h:
        return (
            "SendGrid rejected the credentials. `username` must be "
            "literally the string 'apikey', and `password` must be a "
            "SendGrid API key with the 'Mail Send' permission."
            + detail
        )
    if "amazonaws" in h or "ses" in h:
        return (
            "AWS SES rejected the credentials. Use the SMTP-specific "
            "username/password generated under SES → SMTP settings — "
            "your IAM access key won't work as-is."
            + detail
        )
    return (
        "SMTP authentication failed. Re-check the username and password "
        "in your Streamlit secrets — the value of `password` must be the "
        "SMTP-specific credential from your provider's dashboard, not "
        "your account login password."
        + detail
    )


def send_booking_email(
    *,
    to_email: str,
    customer_name: str,
    token: str,
    service_name: str,
    total_fee: int,
    eta_hours: int,
    shop_name: str = "Click2Serve",
    track_url: str | None = None,
    pay_url: str | None = None,
    timeout: float = 12.0,
) -> tuple[bool, str]:
    """Send a booking-confirmation email. Always returns ``(ok, reason)``.

    Dispatches between transports:
      - Brevo HTTP API if [brevo_api] is configured (no IP whitelist
        needed — bypasses the 525 Unauthorized IP errors that hit
        SMTP from Streamlit Cloud and other shared-IP hosts).
      - SMTP otherwise (works for Gmail, Resend, Mailgun, SendGrid,
        Brevo SMTP if you've whitelisted the host's IP, etc.).

    Never raises — the caller can safely call this from inside the
    booking submit handler without risking the booking itself.
    """
    if not (to_email or "").strip():
        return False, "No customer email on file"

    # Build the message body once; the transports below differ only in
    # how they ship it.
    first_name = (customer_name or "").strip().split()[:1]
    greeting_name = first_name[0] if first_name else "there"
    subject = f"Your booking is confirmed — {token}  ·  {shop_name}"
    plain_lines = [
        f"Hi {greeting_name},",
        "",
        f"We've received your booking at {shop_name}.",
        "",
        f"  Booking number:   {token}",
        f"  Service:          {service_name}",
        f"  Total fee:        Rs. {total_fee}",
        f"  Expected ready:   ~{eta_hours} hours from now",
        "",
    ]
    if track_url:
        plain_lines.append(f"Track your booking:  {track_url}")
    if pay_url:
        plain_lines.append(f"Pay online (UPI):    {pay_url}")
    plain_lines += [
        "",
        f"Save this booking number — you'll need it together with your "
        f"mobile number to track or pay.",
        "",
        f"Thanks,",
        f"{shop_name}",
    ]
    plain_body = "\n".join(plain_lines)
    html_body = _build_html_body(
        greeting_name=greeting_name,
        shop_name=shop_name,
        token=token,
        service_name=service_name,
        total_fee=total_fee,
        eta_hours=eta_hours,
        track_url=track_url,
        pay_url=pay_url,
    )

    # ── Transport selection ───────────────────────────────────────────
    if is_brevo_api_configured():
        return _send_via_brevo_api(
            to_email=to_email.strip(),
            subject=subject,
            html_body=html_body,
            plain_body=plain_body,
            timeout=timeout,
        )

    if not is_smtp_configured():
        return False, (
            "Email is not configured. Add either `[brevo_api]` (HTTP) "
            "or `[smtp]` to your Streamlit secrets."
        )

    return _send_via_smtp(
        to_email=to_email.strip(),
        subject=subject,
        html_body=html_body,
        plain_body=plain_body,
        timeout=timeout,
    )


def send_test_email(*, to_email: str) -> tuple[bool, str]:
    """Send a single 'this is a test' email used by the Settings UI.

    Routes through whichever transport is configured (Brevo HTTP API
    preferred; SMTP fallback). Bypasses no toggle — credentials alone
    are enough to test, so the owner can verify reachability before
    relying on it.
    """
    if not is_email_configured():
        return False, (
            "Email is not configured. Add either a `[brevo_api]` block "
            "(HTTP, recommended for Streamlit Cloud) or a `[smtp]` "
            "block to your Streamlit secrets."
        )
    if not (to_email or "").strip():
        return False, "Please enter an email address to test."

    plain_body = (
        "If you got this email, your Click2Serve email setup is working.\n"
        "You can now turn on booking-confirmation emails for customers."
    )
    # Tiny HTML version so providers don't down-rank the test as
    # text-only spam.
    html_body = (
        "<p>If you got this email, your Click2Serve email setup is "
        "working.</p>"
        "<p>You can now turn on booking-confirmation emails for "
        "customers.</p>"
    )
    subject = "Click2Serve — email transport test"

    if is_brevo_api_configured():
        return _send_via_brevo_api(
            to_email=to_email.strip(),
            subject=subject,
            html_body=html_body,
            plain_body=plain_body,
            timeout=12.0,
        )

    return _send_via_smtp(
        to_email=to_email.strip(),
        subject=subject,
        html_body=html_body,
        plain_body=plain_body,
        timeout=12.0,
    )


# ──────────────────────────────────────────────────────────────────────────
# Brevo HTTP API transport
# ──────────────────────────────────────────────────────────────────────────
def _send_via_brevo_api(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    plain_body: str,
    timeout: float = 12.0,
) -> tuple[bool, str]:
    """POST a single transactional email to Brevo's HTTP API.

    Brevo's HTTP API doesn't have the IP-whitelist requirement that
    blocks their SMTP from shared-IP hosts like Streamlit Cloud. Same
    free 300/day quota, same provider, just a different transport.

    Returns ``(ok, reason)``. Never raises.
    """
    s = _brevo_api_secrets()
    api_key = (s.get("api_key") or "").strip()
    from_email = (s.get("from_email") or "").strip()
    from_name = (s.get("from_name") or "Click2Serve").strip() or "Click2Serve"

    if not api_key:
        return False, (
            "Brevo HTTP API key is missing. Add `api_key` to the "
            "`[brevo_api]` block in your Streamlit secrets."
        )
    if not from_email:
        return False, (
            "Brevo HTTP API needs a `from_email`. Add it to the "
            "`[brevo_api]` block in your Streamlit secrets."
        )

    payload = {
        "sender": {"email": from_email, "name": from_name},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": html_body,
        "textContent": plain_body,
    }
    headers = {
        # Brevo expects this exact header name (no Bearer / Basic prefix).
        "api-key": api_key,
        "accept": "application/json",
        "content-type": "application/json",
    }

    try:
        resp = requests.post(
            _BREVO_API_URL, json=payload, headers=headers, timeout=timeout,
        )
    except requests.RequestException as exc:
        logger.warning("Brevo HTTP API request failed: %s", exc)
        return False, f"Network error contacting Brevo: {exc}"
    except Exception as exc:  # noqa: BLE001 — last-resort safety
        logger.exception("Unexpected Brevo HTTP error: %s", exc)
        return False, f"Unexpected error: {exc}"

    if 200 <= resp.status_code < 300:
        return True, f"Confirmation email sent to {to_email}"

    # Brevo returns JSON error bodies — surface the underlying message
    # so users (and we) can debug from the toast alone.
    detail = ""
    try:
        body = resp.json()
        msg = body.get("message") or body.get("code") or "unknown"
        detail = f" — {msg}"
    except Exception:  # noqa: BLE001
        detail = (resp.text or "")[:200]
        if detail:
            detail = f" — {detail}"

    if resp.status_code == 401:
        return False, (
            "Brevo rejected the API key. Generate a new one at "
            "https://app.brevo.com/settings/keys/api and paste it as "
            "`api_key` in your `[brevo_api]` secrets block."
            + detail
        )
    if resp.status_code == 400 and "sender" in (detail or "").lower():
        return False, (
            "Brevo rejected the sender. The `from_email` in "
            "`[brevo_api]` must be a verified sender at "
            "https://app.brevo.com/senders — your signup email is "
            "verified by default."
            + detail
        )
    return False, f"Brevo HTTP {resp.status_code}{detail}"


# ──────────────────────────────────────────────────────────────────────────
# SMTP transport (legacy — kept for Gmail / Resend / Mailgun / etc.)
# ──────────────────────────────────────────────────────────────────────────
def _send_via_smtp(
    *,
    to_email: str,
    subject: str,
    html_body: str,
    plain_body: str,
    timeout: float = 12.0,
) -> tuple[bool, str]:
    """Send an email via plain smtplib. Returns ``(ok, reason)``.

    Mirrors the previous monolithic ``send_booking_email`` logic but
    factored out so the dispatch layer can pick between transports
    without duplicating the message builder.
    """
    s = _smtp_secrets()
    host = (s["host"] or "").strip()
    port = int(s.get("port") or 587)
    username = (s["username"] or "").strip()
    password = (s["password"] or "").strip()
    use_tls = bool(s.get("use_tls", True))

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = _build_from_header()
    msg["To"] = to_email
    msg.set_content(plain_body)
    msg.add_alternative(html_body, subtype="html")

    try:
        if port == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, timeout=timeout, context=ctx) as smtp:
                smtp.login(username, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=timeout) as smtp:
                smtp.ehlo()
                if use_tls:
                    ctx = ssl.create_default_context()
                    smtp.starttls(context=ctx)
                    smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        logger.warning("SMTP auth failed for %s: %s", host, exc)
        return False, _auth_failure_message(host, exc)
    except smtplib.SMTPException as exc:
        logger.warning("SMTP error sending to %s: %s", to_email, exc)
        return False, f"SMTP error: {exc}"
    except (OSError, TimeoutError) as exc:
        logger.warning("SMTP network error: %s", exc)
        return False, f"Network error contacting {host}: {exc}"
    except Exception as exc:  # noqa: BLE001 — last-resort safety
        logger.exception("Unexpected email error: %s", exc)
        return False, f"Unexpected error: {exc}"

    return True, f"Confirmation email sent to {to_email}"


# ──────────────────────────────────────────────────────────────────────────
# HTML body builder
# ──────────────────────────────────────────────────────────────────────────
def _build_html_body(
    *,
    greeting_name: str,
    shop_name: str,
    token: str,
    service_name: str,
    total_fee: int,
    eta_hours: int,
    track_url: str | None,
    pay_url: str | None,
) -> str:
    """Build the HTML email body. Inline styles only (works in Gmail / Outlook)."""
    cta_blocks = []
    if track_url:
        cta_blocks.append(_button(track_url, "Track booking", "#0F172A"))
    if pay_url:
        cta_blocks.append(_button(pay_url, "Pay online", "#2563EB"))
    cta_html = (
        '<table role="presentation" cellpadding="0" cellspacing="0" border="0" '
        'style="margin-top:18px;"><tr>'
        + "".join(f"<td style='padding-right:8px;'>{b}</td>" for b in cta_blocks)
        + "</tr></table>"
        if cta_blocks else ""
    )

    return f"""
<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><title>Booking confirmed</title></head>
<body style="margin:0; padding:0; background:#F8FAFC; font-family:
  -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
  color:#0F172A;">
  <table role="presentation" cellpadding="0" cellspacing="0" border="0"
         width="100%" style="padding:24px 0;">
    <tr>
      <td align="center">
        <table role="presentation" cellpadding="0" cellspacing="0" border="0"
               width="560" style="max-width:560px; background:#FFFFFF;
               border:1px solid #E2E8F0; border-radius:14px; padding:28px;">

          <tr><td>
            <div style="font-size:11px; font-weight:700; color:#2563EB;
                 text-transform:uppercase; letter-spacing:0.12em;
                 margin-bottom:14px;">Booking confirmed</div>
            <h1 style="margin:0 0 8px; font-size:22px; font-weight:800;
                 letter-spacing:-0.01em; color:#0F172A;">
              Hi {greeting_name}, your booking is in.
            </h1>
            <p style="margin:0 0 18px; color:#64748B; font-size:15px;
                 line-height:1.55;">
              Save the booking number below — you'll need it together
              with your mobile number to track or pay.
            </p>

            <div style="background:#DCFCE7; border:1px solid #16A34A;
                 border-radius:12px; padding:18px 16px; margin:6px 0 18px;
                 text-align:center;">
              <div style="font-size:11px; font-weight:700; color:#15803D;
                   text-transform:uppercase; letter-spacing:0.1em;">
                Your booking number
              </div>
              <div style="font-size:34px; font-weight:900; letter-spacing:
                   0.06em; color:#0F172A; margin-top:6px;
                   font-family: 'Inter', monospace, sans-serif;">{token}</div>
            </div>

            <table role="presentation" cellpadding="0" cellspacing="0" border="0"
                   width="100%" style="border:1px solid #E2E8F0;
                   border-radius:10px; overflow:hidden;">
              <tr>
                <td style="padding:12px 16px; background:#F8FAFC; width:38%;
                     color:#64748B; font-size:13px; font-weight:600;
                     text-transform:uppercase; letter-spacing:0.06em;">Service</td>
                <td style="padding:12px 16px; color:#0F172A; font-size:15px;
                     font-weight:600;">{service_name}</td>
              </tr>
              <tr>
                <td style="padding:12px 16px; background:#F8FAFC; border-top:
                     1px solid #E2E8F0; color:#64748B; font-size:13px;
                     font-weight:600; text-transform:uppercase; letter-spacing:
                     0.06em;">Total fee</td>
                <td style="padding:12px 16px; border-top:1px solid #E2E8F0;
                     color:#0F172A; font-size:15px; font-weight:700;">
                     ₹{total_fee}</td>
              </tr>
              <tr>
                <td style="padding:12px 16px; background:#F8FAFC; border-top:
                     1px solid #E2E8F0; color:#64748B; font-size:13px;
                     font-weight:600; text-transform:uppercase; letter-spacing:
                     0.06em;">Ready in</td>
                <td style="padding:12px 16px; border-top:1px solid #E2E8F0;
                     color:#0F172A; font-size:15px; font-weight:600;">
                     ~{eta_hours} hours</td>
              </tr>
            </table>

            {cta_html}

            <p style="margin:22px 0 0; color:#94A3B8; font-size:12px;
                 line-height:1.55;">
              You're receiving this email because you booked a service at
              {shop_name} via Click2Serve. If this wasn't you, please
              reply to this email and let us know.
            </p>
          </td></tr>
        </table>
      </td>
    </tr>
  </table>
</body>
</html>
"""


def _button(url: str, label: str, bg: str) -> str:
    """Inline-styled CTA button, table-friendly for Gmail / Outlook."""
    return (
        f'<a href="{url}" style="display:inline-block; background:{bg}; '
        f'color:#FFFFFF; text-decoration:none; padding:11px 20px; '
        f'border-radius:8px; font-weight:700; font-size:14px;">{label}</a>'
    )
