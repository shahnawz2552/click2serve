"""Email sending via SMTP (built-in smtplib, zero new dependencies).

Used by Click2Serve to email the customer their booking token + summary
right after a booking is created. Configurable through Streamlit secrets,
and graceful when not configured — pages call ``send_booking_email`` and
get back a ``(ok, reason)`` tuple they can fold into their success toast.

Setup (one-time, owner does this once)
--------------------------------------
The shop owner picks an SMTP provider — most owners will use Gmail, but
Brevo / Mailgun / SendGrid / their own ISP all work. Add credentials to
``.streamlit/secrets.toml`` (or Streamlit Cloud → Manage app → Secrets):

    [smtp]
    host        = "smtp.gmail.com"
    port        = 587
    username    = "yourshop@gmail.com"
    password    = "<app-specific password>"   # NOT your account password
    from_email  = "yourshop@gmail.com"
    from_name   = "Click2Serve Bharatpur"
    use_tls     = true

For Gmail, "password" must be an `App Password
<https://myaccount.google.com/apppasswords>`_ — Google blocks regular
passwords for SMTP. Brevo / Mailgun / SendGrid issue an SMTP key under
their dashboard.

Why smtplib instead of a fancy provider SDK?
- Zero new dependencies (smtplib is Python stdlib).
- Works against any provider — Gmail, Brevo, Mailgun, SendGrid, the
  shop's own ISP, anything that speaks SMTP.
- Trivial to switch later if needed; this module's public surface is
  the only contract pages depend on.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any

import streamlit as st

logger = logging.getLogger(__name__)


def _smtp_secrets() -> dict[str, Any]:
    """Return the [smtp] section of secrets, or empty dict if absent."""
    if not hasattr(st, "secrets"):
        return {}
    try:
        return dict(st.secrets.get("smtp", {}) or {})
    except Exception:  # noqa: BLE001
        return {}


def is_email_configured() -> bool:
    """Return True iff host + username + password + from_email are all set."""
    s = _smtp_secrets()
    return bool(
        (s.get("host") or "").strip()
        and (s.get("username") or "").strip()
        and (s.get("password") or "").strip()
        and (s.get("from_email") or "").strip()
    )


def _build_from_header() -> str:
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
            "Brevo rejected the credentials. Check that:"
            "\n  1. `username` is the EMAIL you signed up with at Brevo"
            " (NOT the literal text 'apikey')."
            "\n  2. `password` is your Brevo SMTP key (from "
            "https://app.brevo.com/settings/keys/smtp — NOT the API key"
            " from the API tab)."
            "\n  3. Your Brevo account's signup email is verified."
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

    Never raises — the caller can safely call this from inside the
    booking submit handler without risking the booking itself.
    """
    if not (to_email or "").strip():
        return False, "No customer email on file"
    if not is_email_configured():
        return False, "Email not configured in secrets.toml"

    s = _smtp_secrets()
    host = (s["host"] or "").strip()
    port = int(s.get("port") or 587)
    username = (s["username"] or "").strip()
    password = (s["password"] or "").strip()
    use_tls = bool(s.get("use_tls", True))

    first_name = (customer_name or "").strip().split()[:1]
    greeting_name = first_name[0] if first_name else "there"

    msg = EmailMessage()
    msg["Subject"] = (
        f"Your booking is confirmed — {token}  ·  {shop_name}"
    )
    msg["From"] = _build_from_header()
    msg["To"] = to_email.strip()
    # Plain-text fallback (always sent — clients that can't render HTML
    # still see something useful).
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
    msg.set_content("\n".join(plain_lines))

    # HTML version — modern but defensive (works in Gmail, Apple Mail,
    # Outlook, mobile clients). Uses inline styles only.
    html = _build_html_body(
        greeting_name=greeting_name,
        shop_name=shop_name,
        token=token,
        service_name=service_name,
        total_fee=total_fee,
        eta_hours=eta_hours,
        track_url=track_url,
        pay_url=pay_url,
    )
    msg.add_alternative(html, subtype="html")

    try:
        if port == 465:
            # Implicit TLS (SMTPS).
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

    return True, f"Confirmation email sent to {to_email.strip()}"


def send_test_email(*, to_email: str) -> tuple[bool, str]:
    """Send a single 'this is a test' email used by the Settings UI.

    Bypasses no toggle — credentials alone are enough to test, so the
    owner can verify SMTP is reachable before relying on it.
    """
    if not is_email_configured():
        return False, (
            "SMTP credentials are not configured. Add the [smtp] block "
            "with host / port / username / password / from_email to "
            "Streamlit secrets."
        )
    if not (to_email or "").strip():
        return False, "Please enter an email address to test."

    s = _smtp_secrets()
    host = (s["host"] or "").strip()
    port = int(s.get("port") or 587)
    username = (s["username"] or "").strip()
    password = (s["password"] or "").strip()
    use_tls = bool(s.get("use_tls", True))

    msg = EmailMessage()
    msg["Subject"] = "Click2Serve — SMTP test message"
    msg["From"] = _build_from_header()
    msg["To"] = to_email.strip()
    msg.set_content(
        "If you got this email, your Click2Serve SMTP setup is working.\n"
        "You can now turn on booking-confirmation emails for customers."
    )

    try:
        if port == 465:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(host, port, timeout=12, context=ctx) as smtp:
                smtp.login(username, password)
                smtp.send_message(msg)
        else:
            with smtplib.SMTP(host, port, timeout=12) as smtp:
                smtp.ehlo()
                if use_tls:
                    ctx = ssl.create_default_context()
                    smtp.starttls(context=ctx)
                    smtp.ehlo()
                smtp.login(username, password)
                smtp.send_message(msg)
    except smtplib.SMTPAuthenticationError as exc:
        return False, _auth_failure_message(host, exc)
    except Exception as exc:  # noqa: BLE001
        return False, f"Could not send test email: {exc}"

    return True, f"Test email sent to {to_email.strip()}"


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
