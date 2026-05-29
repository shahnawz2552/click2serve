"""Customer contact page — shop info + clickable call/WhatsApp/maps links.

Reads everything from ``shop_config`` so the owner only has to fill it in
once (Settings → Section 01) and it shows up here automatically. Empty
fields are hidden gracefully.
"""
from __future__ import annotations

from urllib.parse import quote

import streamlit as st

from core.db import get_shop_config
from core.styles import (
    BORDER, INK, MUTED, PRIMARY, PRIMARY_TINT, SURFACE,
    inject_global_css, section_header,
)

inject_global_css()

shop = get_shop_config() or {}


def _v(key: str, default: str = "") -> str:
    """Return shop_config[key], with None coerced to default."""
    val = shop.get(key)
    return (val or default) or ""


shop_name = _v("shop_name", "Click2Serve")
owner_name = _v("owner_name")
owner_phone = _v("owner_phone")
address = _v("address")
opening_hours = _v("opening_hours")


def _normalize_phone_for_links(phone: str) -> str:
    """Strip spaces / dashes / parentheses; keep digits and a leading '+'.

    Used for ``tel:`` and ``wa.me`` links. We don't try to be smart about
    country codes here — we just clean punctuation.
    """
    if not phone:
        return ""
    cleaned = "".join(c for c in phone if c.isdigit() or c == "+")
    return cleaned


def _wa_me_url(phone: str, prefilled: str = "") -> str:
    """Build a wa.me deep-link. wa.me wants digits only — strip the '+'."""
    digits = _normalize_phone_for_links(phone).lstrip("+")
    if not digits or not digits.isdigit():
        return ""
    if prefilled:
        return f"https://wa.me/{digits}?text={quote(prefilled)}"
    return f"https://wa.me/{digits}"


def _maps_url(addr: str) -> str:
    """Google Maps search URL for the given address string."""
    if not addr:
        return ""
    return f"https://www.google.com/maps/search/?api=1&query={quote(addr)}"


# ── Header ──────────────────────────────────────────────────────────────────
section_header(
    eyebrow="Contact",
    title="Get in touch.",
    subtitle=f"Questions, complaints, or just need help? Reach out to "
             f"{shop_name} directly.",
)


# ── Empty-state fallback if the owner hasn't filled in shop info yet ──────
if not (owner_phone or address or opening_hours):
    st.info(
        "The shop owner hasn't published their contact details yet. "
        "Please come back soon."
    )
    st.stop()


# ── Phone / WhatsApp card ──────────────────────────────────────────────────
if owner_phone:
    st.markdown(
        f"<div class='c2s-cat'>Call or WhatsApp</div>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(
            f"<div style='font-size:1.6rem; font-weight:800; "
            f"letter-spacing:-0.02em; color:{INK}; margin-bottom:0.2rem;'>"
            f"📞 {owner_phone}</div>"
            + (f"<div style='color:{MUTED}; font-size:0.9rem; "
               f"margin-bottom:0.8rem;'>{owner_name}</div>"
               if owner_name else
               "<div style='height:0.6rem;'></div>"),
            unsafe_allow_html=True,
        )

        c1, c2 = st.columns(2)
        tel = _normalize_phone_for_links(owner_phone)
        wa = _wa_me_url(
            owner_phone,
            prefilled=f"Hi {shop_name}, I have a question about my booking.",
        )

        with c1:
            if tel:
                st.markdown(
                    f"""
                    <a href="tel:{tel}" style="display:block; text-align:center;
                       background:{INK}; color:#F1ECE0;
                       padding:0.7rem 1rem; font-weight:600; font-size:0.95rem;
                       text-decoration:none; border:1px solid {INK};
                       border-radius:6px;">
                        📞 Call now
                    </a>
                    """,
                    unsafe_allow_html=True,
                )
        with c2:
            if wa:
                st.link_button(
                    "💬 Open WhatsApp",
                    wa,
                    use_container_width=True,
                )
            else:
                st.caption(
                    "WhatsApp link unavailable — phone may be missing the "
                    "country code."
                )


# ── Address / Maps card ────────────────────────────────────────────────────
if address:
    st.markdown(
        "<div style='height:1.2rem;'></div>"
        "<div class='c2s-cat'>Visit the shop</div>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(
            f"<div style='font-size:1rem; line-height:1.5; color:{INK}; "
            f"white-space:pre-wrap; margin-bottom:0.8rem;'>📍 {address}</div>",
            unsafe_allow_html=True,
        )

        # Embedded Google Map — keyless iframe. The owner pastes the
        # "Embed a map" URL from Google Maps into Settings; we fall
        # back to a generic search-by-address embed if they haven't.
        embed_url = (_v("maps_embed_url") or "").strip()
        if not embed_url:
            embed_url = (
                "https://www.google.com/maps?q="
                + quote(address) + "&output=embed"
            )
        st.markdown(
            f'<iframe src="{embed_url}" width="100%" height="280" '
            f'style="border:0; border-radius:10px; margin-bottom:0.8rem;" '
            f'loading="lazy" referrerpolicy="no-referrer-when-downgrade" '
            f'allowfullscreen></iframe>',
            unsafe_allow_html=True,
        )

        # Prefer the shop's shareable maps URL (https://maps.app.goo.gl/...)
        # which opens the actual Google Business Profile; fall back to
        # a search-by-address URL otherwise.
        link_url = (_v("maps_url") or "").strip() or _maps_url(address)
        if link_url:
            st.link_button(
                "Open in Google Maps →",
                link_url,
                use_container_width=True,
            )


# ── Opening hours ──────────────────────────────────────────────────────────
if opening_hours:
    st.markdown(
        "<div style='height:1.2rem;'></div>"
        "<div class='c2s-cat'>Open hours</div>",
        unsafe_allow_html=True,
    )
    with st.container(border=True):
        st.markdown(
            f"<div style='font-size:1rem; color:{INK}; "
            f"white-space:pre-wrap;'>🕒 {opening_hours}</div>",
            unsafe_allow_html=True,
        )


# ── Common questions (static, helps deflect support) ──────────────────────
st.markdown(
    "<div style='height:1.6rem;'></div>"
    "<div class='c2s-cat'>Common questions</div>"
    f"<h3 style='margin:0 0 0.8rem !important; font-size:1.1rem !important; "
    f"font-weight:700 !important; color:{INK} !important;'>"
    "Before you call, you might find your answer here.</h3>",
    unsafe_allow_html=True,
)

with st.expander("How do I track my booking?"):
    st.markdown(
        "Open the **Track booking** page in the menu and enter your token "
        "and the mobile number you used at booking. You'll see the latest "
        "status and an estimated ready-by time."
    )

with st.expander("How can I pay online?"):
    st.markdown(
        "Open the **Pay online** page, look up your booking with token + "
        "phone, then scan the QR code with any UPI app (PhonePe, GPay, "
        "Paytm…) or tap *Open UPI app on this phone*. After paying, copy "
        "the UTR from your UPI app and paste it back to confirm."
    )

with st.expander("I lost my token — what do I do?"):
    st.markdown(
        "No problem. Open **Track booking** and switch to the "
        "**My bookings (by phone)** tab. Enter the mobile number you used "
        "at booking and you'll see every booking you've ever made — pick "
        "the right token from there."
    )

with st.expander("Can I cancel a booking?"):
    st.markdown(
        f"Yes — please call or WhatsApp {shop_name} on the number above "
        "and we'll process it. Refunds (if any) follow your UPI app's "
        "usual reversal timing."
    )
