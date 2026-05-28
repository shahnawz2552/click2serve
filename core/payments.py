"""Payment helpers — UPI deep links + QR code rendering.

The MVP flow is UPI-based, which is how the vast majority of Indian small
shops actually accept online payments today:

  1. Owner configures their UPI VPA (e.g. ``shop@okaxis``) in Settings.
  2. Customer opens the Pay page for a booking; the app builds a UPI
     deep-link URI and renders it as a QR code.
  3. Customer scans / taps, pays from any UPI app (PhonePe, GPay, Paytm).
  4. Customer pastes the 12-digit UTR back into the app and submits.
  5. Owner verifies the UTR in their own UPI app and confirms in the
     bookings queue (one click → ``payment_method='UPI'``, status='Paid').

For full auto-reconciliation, swap ``build_upi_uri`` for a Razorpay /
Cashfree integration — the shop_config table already has a placeholder
for ``razorpay_key_id`` to make that drop-in.
"""
from __future__ import annotations

import re
from urllib.parse import quote

import segno

# UTR is the 12-digit reference UPI apps return after a successful payment.
# Some banks emit longer alphanumeric refs; allow 10–22 chars to be safe.
UTR_PATTERN = re.compile(r"^[A-Za-z0-9]{10,22}$")

# Indian UPI VPA: alphanumeric (with . _ -) followed by @handle
VPA_PATTERN = re.compile(r"^[a-zA-Z0-9._\-]{2,256}@[a-zA-Z]{2,64}$")


def is_valid_vpa(vpa: str) -> bool:
    return bool(vpa and VPA_PATTERN.match(vpa.strip()))


def is_valid_utr(utr: str) -> bool:
    return bool(utr and UTR_PATTERN.match(utr.strip()))


def build_upi_uri(
    *, payee_vpa: str, payee_name: str, amount: int | float, note: str
) -> str:
    """Build a UPI deep-link URI compliant with NPCI's spec.

    See: https://upi-developer.npci.org.in/#/spec/version/2.0/deeplink
    Format: ``upi://pay?pa=<vpa>&pn=<name>&am=<amount>&tn=<note>&cu=INR``

    All values are URL-encoded.  Amount is in rupees with up to 2 decimals.
    """
    params = {
        "pa": payee_vpa.strip(),
        "pn": payee_name.strip() or "Click2Serve",
        "am": f"{float(amount):.2f}",
        "tn": (note or "").strip()[:80],  # transaction note, capped
        "cu": "INR",
    }
    query = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items())
    return f"upi://pay?{query}"


def qr_svg(data: str, *, scale: int = 6, dark: str = "#1B4F8A") -> str:
    """Return an inline SVG string for the given payload.

    Uses ``segno`` (pure-Python, no Pillow dependency). The SVG embeds
    explicit width/height attributes so it renders at a fixed size when
    inlined via ``st.markdown(..., unsafe_allow_html=True)`` — without
    them, some browsers render the SVG as 0x0 inside Streamlit's flex
    column layout.
    """
    qr = segno.make(data, error="m")
    import io as _io

    buf = _io.BytesIO()
    qr.save(
        buf, kind="svg", scale=scale, dark=dark, light="#ffffff",
        xmldecl=False, svgns=True,
        # omitsize=False (default) — keep width/height so the QR has an
        # intrinsic size when embedded as raw HTML inside a flex layout.
        border=2,
    )
    return buf.getvalue().decode("utf-8")
