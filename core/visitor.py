"""Visitor counter — tiny social-proof badge on the customer pages.

Two responsibilities:

1. ``track_session_visit()`` records a visit exactly once per Streamlit
   session, so the same customer flicking between Home / Book / Track
   doesn't inflate the count. Owners are excluded — they don't count
   as visitors.

2. ``visitor_badge_html()`` renders a small "🧑 N people have visited
   today · X total" pill suitable for a footer. Uses the same colour
   tokens as the rest of the design system.

The counter table itself (and the read/write helpers) live in
``core.db``; this module is just the *page-level glue*.
"""
from __future__ import annotations

import streamlit as st

from core.db import get_visit_stats, record_visit
from core.styles import BORDER, INK, MUTED, PRIMARY


_SESSION_KEY = "_c2s_visit_recorded"


def track_session_visit() -> None:
    """Increment the daily counter the first time a session lands on
    a customer page. Owners are skipped.

    Idempotent within a session — guarded by ``st.session_state`` so
    navigating between pages doesn't double-count. Wraps ``record_visit``
    in a try/except so a counter outage never blocks the page load.
    """
    if st.session_state.get("logged_in"):
        return
    if st.session_state.get(_SESSION_KEY):
        return
    try:
        record_visit()
    except Exception:
        # core.db.record_visit already swallows DB failures; this is
        # belt-and-braces in case future versions of the helper raise.
        pass
    st.session_state[_SESSION_KEY] = True


def visitor_badge_html(stats: dict[str, int] | None = None) -> str:
    """Return a single-line social-proof badge.

    Pulls aggregates from ``get_visit_stats()`` if not provided. Falls
    back to a quiet '...' placeholder when stats are unavailable
    (e.g. brief DB hiccup) so the footer never looks broken.
    """
    if stats is None:
        try:
            stats = get_visit_stats()
        except Exception:
            stats = None

    if not stats or stats.get("all_time", 0) <= 0:
        # No data yet — render a generic line so the footer still has
        # the visual weight of a counter without misleading the customer.
        return (
            f'<div style="text-align:center; color:{MUTED}; '
            f'font-size:0.78rem; padding:0.4rem 0;">'
            f'\U0001F44B Welcome \u2014 you are one of our first visitors.'
            f'</div>'
        )

    today_n = int(stats.get("today") or 0)
    all_n = int(stats.get("all_time") or 0)
    last7 = int(stats.get("last7") or 0)

    today_str = (
        f"{today_n} {'visitor' if today_n == 1 else 'visitors'} today"
    )
    weekly_str = (
        f"{last7:,} this week" if last7 else ""
    )
    total_str = f"{all_n:,} total"

    extra = f" \u00b7 {weekly_str}" if weekly_str else ""

    return (
        f'<div style="display:flex; align-items:center; '
        f'justify-content:center; gap:0.45rem; color:{MUTED}; '
        f'font-size:0.78rem; padding:0.5rem 0; '
        f'border-top:1px solid {BORDER}; margin-top:1rem;">'
        f'<span style="display:inline-flex; width:6px; height:6px; '
        f'border-radius:50%; background:{PRIMARY};"></span>'
        f'<span><b style="color:{INK}; font-weight:700;">'
        f'{today_str}</b>{extra} \u00b7 {total_str}</span>'
        f'</div>'
    )
