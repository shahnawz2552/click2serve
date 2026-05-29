"""SEO + Local Business structured data for Click2Serve.

The point of this module is to make the shop discoverable and bookable
directly from Google Search and Google Maps. Three things together
produce the "Book Now" green button on a Google Business Profile:

1. The shop owner registers a Google Business Profile (manual, one-time,
   at https://business.google.com). That's what makes the shop appear in
   "passport service near me" results in the first place — Google can't
   index something it doesn't know exists.

2. The Business Profile's "Appointment URL" points at this Streamlit
   app, ideally with a UTM tag like ``?utm_source=google&utm_medium=gbp``
   so we can track inbound traffic.

3. The pages of this app emit a ``LocalBusiness`` schema.org JSON-LD
   block that Google reads to confirm shop name, hours, phone, address,
   and that the URL is a booking page. Without the JSON-LD, Google
   often *won't* surface the Book Now button even if the appointment URL
   is set, because it can't tell the URL is a real business landing
   page.

This module is responsible for #3 and for a tiny "Welcome from Google!"
banner shown to traffic that arrives with the UTM tag.

Public surface:
    inject_local_business_jsonld()  - drop one <script type="application/ld+json">
                                      block on the current page using the
                                      latest shop_config values.
    google_traffic_banner()         - render a small one-liner banner if
                                      the visitor arrived from Google.
"""
from __future__ import annotations

import json
import logging
from typing import Any

import streamlit as st

logger = logging.getLogger(__name__)


def _shop() -> dict[str, Any]:
    """Read the singleton shop_config row, returning {} on any failure.

    Lazy import to avoid a circular import — core.db imports streamlit
    and so does this module; keeping the import inside the function
    means seo.py stays usable even before core.db is fully loaded.
    """
    try:
        from core.db import get_shop_config

        return get_shop_config() or {}
    except Exception as exc:  # noqa: BLE001
        logger.debug("seo: shop_config unavailable: %s", exc)
        return {}


def _split_opening_hours(hours_text: str) -> list[str] | None:
    """Convert "Mon-Sat 9 AM - 9 PM" into schema.org ``Mo-Sa 09:00-21:00``.

    Google is forgiving here — if we can't parse cleanly we return the
    raw string in a list, which still helps. The goal is best-effort,
    not a calendar parser.
    """
    text = (hours_text or "").strip()
    if not text:
        return None
    # We don't try to be clever; embed as a single human string.
    return [text]


def build_local_business_jsonld(
    *, page_url: str | None = None,
) -> dict[str, Any] | None:
    """Build a schema.org ``LocalBusiness`` payload from shop_config.

    Returns ``None`` when the shop has no name (config never seeded) so
    callers can skip injection without polluting the page.
    """
    shop = _shop()
    name = (shop.get("shop_name") or "").strip()
    if not name:
        return None

    business_url = (shop.get("business_url") or "").strip() or page_url or ""
    address = (shop.get("address") or "").strip()
    phone = (shop.get("owner_phone") or "").strip()
    maps_url = (shop.get("maps_url") or "").strip()
    place_id = (shop.get("place_id") or "").strip()

    payload: dict[str, Any] = {
        "@context": "https://schema.org",
        "@type": "LocalBusiness",
        "name": name,
        "description": (
            f"Online booking for government paperwork services at {name}. "
            "Aadhaar, PAN, passport, driving licence, electricity bills "
            "and more — book in 60 seconds, pay online, track by SMS."
        ),
    }
    if business_url:
        payload["url"] = business_url
    if phone:
        payload["telephone"] = phone
    if address:
        payload["address"] = {
            "@type": "PostalAddress",
            "streetAddress": address,
        }

    hours = _split_opening_hours(shop.get("opening_hours"))
    if hours:
        payload["openingHours"] = hours

    lat = shop.get("latitude")
    lng = shop.get("longitude")
    if lat is not None and lng is not None:
        try:
            payload["geo"] = {
                "@type": "GeoCoordinates",
                "latitude": float(lat),
                "longitude": float(lng),
            }
        except (TypeError, ValueError):
            pass

    same_as: list[str] = []
    if maps_url:
        same_as.append(maps_url)
    if same_as:
        payload["sameAs"] = same_as

    if place_id:
        # Surface the Google Place ID so reviewers / aggregators can
        # cross-reference. Not standard schema.org but harmless.
        payload["identifier"] = {
            "@type": "PropertyValue",
            "propertyID": "googlePlaceId",
            "value": place_id,
        }

    if business_url:
        # Marks this URL as the place customers can book directly —
        # this is what tells Google "show the Book Now button".
        payload["potentialAction"] = {
            "@type": "ReserveAction",
            "target": {
                "@type": "EntryPoint",
                "urlTemplate": business_url,
                "actionPlatform": [
                    "http://schema.org/DesktopWebPlatform",
                    "http://schema.org/MobileWebPlatform",
                ],
            },
            "result": {"@type": "Reservation", "name": "Book a service"},
        }

    return payload


def inject_local_business_jsonld(*, page_url: str | None = None) -> None:
    """Drop a single LocalBusiness JSON-LD <script> on the current page.

    Idempotent within a single Streamlit run — guarded by session_state
    so multi-page apps don't emit it twice.
    """
    if st.session_state.get("_c2s_jsonld_injected"):
        return
    payload = build_local_business_jsonld(page_url=page_url)
    if not payload:
        return
    # ensure_ascii=False so emoji / non-Latin shop names render correctly.
    body = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
    st.markdown(
        f'<script type="application/ld+json">{body}</script>',
        unsafe_allow_html=True,
    )
    st.session_state["_c2s_jsonld_injected"] = True


def google_traffic_banner() -> None:
    """Show a one-line welcome banner when the visitor came from Google.

    We check ``utm_source`` in the query string. The expected URL the
    shop owner pastes into their Google Business Profile is something
    like ``https://yourshop.streamlit.app/?utm_source=google&utm_medium=gbp``.
    """
    try:
        params = st.query_params
        source = (params.get("utm_source") or "").lower()
    except Exception:  # noqa: BLE001
        return
    if source != "google":
        return

    # Show once per session — don't nag the customer if they navigate
    # around the app.
    if st.session_state.get("_c2s_google_welcome_shown"):
        return

    st.markdown(
        """
        <div style="background: #DBEAFE; border:1px solid #93C5FD;
                    border-left:4px solid #2563EB; border-radius:10px;
                    padding:0.7rem 0.95rem; margin-bottom:0.9rem;
                    font-size:0.88rem; color:#1E3A8A;">
          <b>Welcome from Google!</b> You found us on Maps.
          Book any service below in 60 seconds — no signup, no app install.
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.session_state["_c2s_google_welcome_shown"] = True
