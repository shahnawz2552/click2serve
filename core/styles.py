"""Global stylesheet + reusable HTML helpers for Click2Serve.

Mobile-first consumer-app aesthetic: clean off-white background, generous
white cards with 1px hairline borders + subtle shadow, deep blue primary
action color, soft pastel category/status pills, 8px corner radii, and
44px minimum touch targets on every clickable element.

Public surface used by pages:
    inject_global_css()         — drop the CSS into the current page once
    section_header(...)         — page-title block (eyebrow + h1 + subtitle)
    category_badge(category)    — colored pill for a service category
    status_badge(status)        — colored pill for a booking status
    payment_badge(state)        — colored pill for payment status
    trust_badge(icon, label)    — small white card used in the home hero row
    progress_steps(steps, cur)  — step bar (used on the booking page)
    status_timeline(status)     — Booked → ... → Delivered timeline
    kpi_card(icon, value, ...)  — dashboard KPI tile with colored icon
    success_token_card(token)   — large green success card with the token

The helpers all return HTML strings; pages wrap them in
``st.markdown(..., unsafe_allow_html=True)``.
"""
from __future__ import annotations

import streamlit as st

# ── Brand palette ───────────────────────────────────────────────────────────
PRIMARY = "#2563EB"          # action blue
PRIMARY_DARK = "#1D4ED8"
PRIMARY_TINT = "#DBEAFE"     # 12% blue, used for badges
INK = "#0F172A"              # body text
MUTED = "#64748B"            # secondary / helper text
HEADING_2 = "#374151"        # h2/h3
BG = "#F8FAFC"               # page background
SURFACE = "#FFFFFF"          # cards, sidebar
BORDER = "#E2E8F0"           # hairline border
BORDER_STRONG = "#CBD5E1"

SUCCESS = "#16A34A"
SUCCESS_BG = "#DCFCE7"
SUCCESS_TEXT = "#15803D"

WARNING = "#D97706"
WARNING_BG = "#FEF3C7"
WARNING_TEXT = "#92400E"

DANGER = "#DC2626"
DANGER_BG = "#FEE2E2"
DANGER_TEXT = "#B91C1C"

TEAL_BG = "#CCFBF1"
TEAL_TEXT = "#0F766E"

GRAY_BG = "#F1F5F9"
GRAY_TEXT = "#475569"


# ──────────────────────────────────────────────────────────────────────────────
# Global stylesheet
# ──────────────────────────────────────────────────────────────────────────────
_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800&display=swap');

/* ── Hide Streamlit chrome ──────────────────────────────────────── */
#MainMenu {{ visibility: hidden; }}
footer {{ visibility: hidden; }}
header[data-testid="stHeader"] {{ background: transparent; height: 0; }}
[data-testid="stToolbar"] {{ display: none; }}
[data-testid="stStatusWidget"] {{ display: none; }}
[data-testid="stDecoration"] {{ display: none; }}

/* ── Tighten layout (don't waste mobile space) ─────────────────── */
section.main > div.block-container {{
    padding-top: 0.8rem;
    padding-bottom: 4rem;
    padding-left: 1rem;
    padding-right: 1rem;
    max-width: 1080px;
}}

/* ── Base typography & background ──────────────────────────────── */
html, body, [data-testid="stAppViewContainer"], .stApp {{
    background: {BG} !important;
    color: {INK} !important;
}}
html, body, [class*="css"], [class*="st-"] {{
    font-family: 'Inter', system-ui, -apple-system, "Segoe UI", sans-serif !important;
    color: {INK};
    -webkit-font-smoothing: antialiased;
    text-rendering: optimizeLegibility;
}}

/* Streamlit's default H1 is huge; override globally */
h1 {{
    font-size: 1.4rem !important;
    font-weight: 700 !important;
    color: {INK} !important;
    letter-spacing: -0.01em;
    line-height: 1.25 !important;
    margin-bottom: 0.4rem !important;
}}
h2 {{
    font-size: 1.15rem !important;
    font-weight: 700 !important;
    color: {INK} !important;
    letter-spacing: -0.01em;
}}
h3, h4 {{
    font-size: 1rem !important;
    font-weight: 600 !important;
    color: {HEADING_2} !important;
    letter-spacing: 0;
}}
p, span, label, div {{ color: {INK}; }}

/* ── Cards (st.container border=True) ──────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {SURFACE} !important;
    border: 1px solid {BORDER} !important;
    border-radius: 12px !important;
    padding: 1rem !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    transition: box-shadow 0.15s ease, border-color 0.15s ease;
}}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    box-shadow: 0 2px 6px rgba(15, 23, 42, 0.07);
    border-color: {BORDER_STRONG} !important;
}}

/* ── Buttons — full-width on mobile, 8px radius, no uppercase ───── */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button {{
    width: 100%;
    border-radius: 8px !important;
    font-weight: 600 !important;
    font-size: 0.92rem !important;
    padding: 0.65rem 1.2rem !important;
    min-height: 44px;
    border: 1px solid {BORDER_STRONG} !important;
    background: {SURFACE} !important;
    color: {INK} !important;
    text-transform: none !important;
    letter-spacing: 0;
    transition: all 0.15s ease;
}}
.stButton > button:hover,
.stDownloadButton > button:hover,
.stFormSubmitButton > button:hover {{
    background: {GRAY_BG} !important;
    border-color: {BORDER_STRONG} !important;
}}

/* Primary buttons — solid blue */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {{
    background: {PRIMARY} !important;
    color: #FFFFFF !important;
    border: 1px solid {PRIMARY} !important;
    box-shadow: 0 1px 3px rgba(37, 99, 235, 0.18);
}}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {{
    background: {PRIMARY_DARK} !important;
    border-color: {PRIMARY_DARK} !important;
    box-shadow: 0 2px 6px rgba(37, 99, 235, 0.30);
}}
.stButton > button[kind="primary"]:disabled {{
    opacity: 0.55;
    box-shadow: none;
}}

/* ── Page links (sidebar nav + inline) ─────────────────────────── */
a[data-testid="stPageLink-NavLink"] {{
    border-radius: 8px !important;
    font-weight: 500;
    min-height: 40px;
}}
a[data-testid="stPageLink-NavLink"]:hover {{
    background: {PRIMARY_TINT} !important;
    color: {PRIMARY_DARK} !important;
}}

/* ── Inputs ─────────────────────────────────────────────────────── */
input, textarea, .stTextInput input, .stNumberInput input {{
    border-radius: 8px !important;
    font-size: 0.92rem !important;
    min-height: 40px;
}}
.stTextInput > div > div,
.stNumberInput > div,
.stSelectbox > div > div,
.stDateInput > div > div,
.stTextArea > div > div {{
    border-radius: 8px !important;
    border-color: {BORDER} !important;
    background: {SURFACE};
}}
.stTextInput > div > div:focus-within,
.stNumberInput > div:focus-within,
.stSelectbox > div > div:focus-within {{
    border-color: {PRIMARY} !important;
    box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.15);
}}

/* ── Sidebar ────────────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background: {SURFACE} !important;
    border-right: 1px solid {BORDER};
}}
section[data-testid="stSidebar"] > div:first-child {{
    background: {SURFACE} !important;
}}
[data-testid="stSidebarNav"] {{
    padding-top: 0.4rem;
}}

/* ── Metrics — clean cards ──────────────────────────────────────── */
[data-testid="stMetric"] {{
    background: {SURFACE};
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 1rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
}}
[data-testid="stMetricValue"] {{
    font-size: 1.6rem !important;
    font-weight: 700 !important;
    color: {INK} !important;
    letter-spacing: -0.02em;
}}
[data-testid="stMetricLabel"] {{
    color: {MUTED} !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.74rem !important;
}}

/* ── Alerts ─────────────────────────────────────────────────────── */
[data-testid="stAlert"] {{
    border-radius: 12px !important;
    border-left-width: 4px !important;
}}

/* ── Tables / DataFrames ───────────────────────────────────────── */
[data-testid="stDataFrame"] {{
    border-radius: 12px !important;
    overflow: hidden;
    border: 1px solid {BORDER};
}}

/* ── Page-title block (used by section_header) ──────────────────── */
.c2s-page-head {{ margin-bottom: 1.2rem; }}
.c2s-eyebrow {{
    display: inline-block;
    font-size: 0.74rem;
    font-weight: 600;
    color: {PRIMARY};
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.4rem;
}}
.c2s-page-title {{
    font-size: 1.4rem !important;
    font-weight: 700 !important;
    color: {INK} !important;
    letter-spacing: -0.01em;
    margin: 0 0 0.3rem !important;
    line-height: 1.25 !important;
}}
.c2s-page-sub {{
    color: {MUTED};
    font-size: 0.9rem;
    margin: 0;
    line-height: 1.5;
}}

/* ── Section subhead (used in form groups) ─────────────────────── */
.c2s-subhead {{
    font-size: 0.78rem;
    font-weight: 700;
    color: {HEADING_2};
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin: 0.6rem 0 0.6rem;
}}

/* ── Pills ──────────────────────────────────────────────────────── */
.c2s-pill {{
    display: inline-block;
    padding: 0.18rem 0.65rem;
    border-radius: 999px;
    font-size: 0.74rem;
    font-weight: 600;
    line-height: 1.4;
    letter-spacing: 0;
}}

/* ── Service price + ETA on home cards ─────────────────────────── */
.c2s-price {{
    font-size: 1.1rem;
    font-weight: 700;
    color: {PRIMARY};
}}
.c2s-eta {{
    font-size: 0.85rem;
    color: {MUTED};
    font-weight: 500;
}}

/* ── Token display (large blue, used on book + track) ──────────── */
.c2s-token {{
    font-size: 1.6rem;
    font-weight: 800;
    color: {PRIMARY};
    letter-spacing: 0.05em;
    line-height: 1;
}}

/* ── Mobile breakpoint ─────────────────────────────────────────── */
@media (max-width: 640px) {{
    section.main > div.block-container {{
        padding-left: 0.8rem;
        padding-right: 0.8rem;
    }}
    h1, .c2s-page-title {{ font-size: 1.3rem !important; }}
    .stButton > button {{ font-size: 0.9rem !important; }}
    [data-testid="stMetricValue"] {{ font-size: 1.4rem !important; }}
}}
</style>
"""


def inject_global_css() -> None:
    """Drop the brand stylesheet into the current page exactly once."""
    if not st.session_state.get("_c2s_css_injected"):
        st.markdown(_CSS, unsafe_allow_html=True)
        st.session_state["_c2s_css_injected"] = True


# ──────────────────────────────────────────────────────────────────────────────
# Reusable HTML helpers
# ──────────────────────────────────────────────────────────────────────────────
def section_header(eyebrow: str = "", title: str = "",
                   subtitle: str = "") -> None:
    """Render the standard page-title block."""
    eb = f'<div class="c2s-eyebrow">{eyebrow}</div>' if eyebrow else ""
    sub = f'<p class="c2s-page-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f'<div class="c2s-page-head">{eb}'
        f'<h1 class="c2s-page-title">{title}</h1>{sub}</div>',
        unsafe_allow_html=True,
    )


def subhead(text: str) -> None:
    st.markdown(f'<div class="c2s-subhead">{text}</div>',
                unsafe_allow_html=True)


# ── Pills ───────────────────────────────────────────────────────────────────
def category_badge(category: str) -> str:
    """Pill colored by service-category family."""
    cat = (category or "").lower()
    if "govern" in cat or "vehicle" in cat or "id" in cat:
        bg, fg = PRIMARY_TINT, PRIMARY_DARK
    elif "payment" in cat or "bill" in cat:
        bg, fg = SUCCESS_BG, SUCCESS_TEXT
    elif "document" in cat:
        bg, fg = WARNING_BG, WARNING_TEXT
    else:
        bg, fg = GRAY_BG, GRAY_TEXT
    return (
        f'<span class="c2s-pill" style="background:{bg}; color:{fg};">'
        f'{category}</span>'
    )


_STATUS_PILL = {
    "Pending":     (GRAY_BG,    GRAY_TEXT),
    "In Progress": (PRIMARY_TINT, PRIMARY_DARK),
    "Ready":       (SUCCESS_BG,  SUCCESS_TEXT),
    "Delivered":   (TEAL_BG,     TEAL_TEXT),
    "Cancelled":   (DANGER_BG,   DANGER_TEXT),
}


def status_badge(status: str, *, big: bool = False) -> str:
    """Pill for a booking status."""
    bg, fg = _STATUS_PILL.get(status, (GRAY_BG, GRAY_TEXT))
    if big:
        return (
            f'<span class="c2s-pill" style="background:{bg}; color:{fg}; '
            f'font-size:0.95rem; padding:0.4rem 0.95rem;">{status}</span>'
        )
    return (
        f'<span class="c2s-pill" style="background:{bg}; color:{fg};">'
        f'{status}</span>'
    )


_PAYMENT_PILL = {
    "verified":  (SUCCESS_BG, SUCCESS_TEXT, "Payment verified"),
    "submitted": (WARNING_BG, WARNING_TEXT, "Awaiting verification"),
    "rejected":  (DANGER_BG,  DANGER_TEXT,  "Payment rejected"),
    "unpaid":    (GRAY_BG,    GRAY_TEXT,    "Unpaid"),
}


def payment_badge(payment_status: str) -> str:
    bg, fg, label = _PAYMENT_PILL.get(
        (payment_status or "unpaid"),
        (GRAY_BG, GRAY_TEXT, payment_status or "Unpaid"),
    )
    return (
        f'<span class="c2s-pill" style="background:{bg}; color:{fg};">'
        f'{label}</span>'
    )


# ── Trust badge (home hero row) ─────────────────────────────────────────────
def trust_badge(icon: str, label: str) -> str:
    return (
        f'<div style="background:{SURFACE}; border:1px solid {BORDER}; '
        f'border-radius:10px; padding:0.85rem 0.6rem; text-align:center;">'
        f'<div style="font-size:1.5rem; line-height:1;">{icon}</div>'
        f'<div style="font-size:0.85rem; font-weight:600; color:{INK}; '
        f'margin-top:0.4rem;">{label}</div>'
        f'</div>'
    )


# ── KPI card (dashboard) ────────────────────────────────────────────────────
def kpi_card(icon: str, value: str, label: str,
             color: str = PRIMARY) -> str:
    """Card with a tinted square icon, big number, small caps label."""
    tint = f"{color}1F"  # ~12% alpha hex (8-char form)
    return (
        f'<div style="background:{SURFACE}; border:1px solid {BORDER}; '
        f'border-radius:12px; padding:1rem; box-shadow:0 1px 2px '
        f'rgba(15,23,42,0.04);">'
        f'<div style="width:36px; height:36px; border-radius:8px; '
        f'background:{tint}; color:{color}; display:inline-flex; '
        f'align-items:center; justify-content:center; font-size:1.1rem; '
        f'margin-bottom:0.55rem;">{icon}</div>'
        f'<div style="font-size:1.6rem; font-weight:800; color:{INK}; '
        f'line-height:1; letter-spacing:-0.02em;">{value}</div>'
        f'<div style="font-size:0.74rem; color:{MUTED}; font-weight:600; '
        f'margin-top:0.4rem; text-transform:uppercase; letter-spacing:'
        f'0.06em;">{label}</div>'
        f'</div>'
    )


# ── Progress steps (booking page) ──────────────────────────────────────────
def progress_steps(steps: list[str], current: int) -> str:
    """Horizontal step bar — ``current`` is 1-indexed."""
    parts: list[str] = []
    for i, label in enumerate(steps, start=1):
        is_active = (i == current)
        is_done = (i < current)
        if is_done or is_active:
            bg, border, fg = PRIMARY, PRIMARY, "#FFFFFF"
            glyph = "✓" if is_done else str(i)
        else:
            bg, border, fg = SURFACE, BORDER_STRONG, "#94A3B8"
            glyph = str(i)
        text_color = (
            PRIMARY if is_active
            else INK if is_done
            else MUTED
        )
        text_weight = 700 if is_active else 600 if is_done else 500
        parts.append(
            f'<div style="display:flex; flex-direction:column; '
            f'align-items:center; flex:1;">'
            f'<div style="width:32px; height:32px; border-radius:50%; '
            f'background:{bg}; border:2px solid {border}; color:{fg}; '
            f'display:inline-flex; align-items:center; justify-content:'
            f'center; font-size:0.85rem; font-weight:700; line-height:1;">'
            f'{glyph}</div>'
            f'<div style="font-size:0.78rem; font-weight:{text_weight}; '
            f'color:{text_color}; text-align:center; margin-top:0.4rem;">'
            f'{label}</div>'
            f'</div>'
        )
        if i < len(steps):
            connector = PRIMARY if is_done else BORDER
            parts.append(
                f'<div style="flex:0.6; height:2px; background:{connector}; '
                f'margin-top:1rem;"></div>'
            )
    return (
        f'<div style="display:flex; align-items:flex-start; padding:0.6rem 0 '
        f'1.4rem;">{"".join(parts)}</div>'
    )


# ── Status timeline (track page) ───────────────────────────────────────────
_STATUS_TO_TIMELINE_INDEX = {
    "Pending":     0,   # Booked
    "In Progress": 1,
    "Ready":       2,
    "Delivered":   3,
    "Cancelled":   -1,
}


def status_timeline(current_status: str) -> str:
    """Booked → In Progress → Ready → Delivered horizontal timeline."""
    if current_status == "Cancelled":
        return (
            f'<div style="background:{DANGER_BG}; color:{DANGER_TEXT}; '
            f'border:1px solid {DANGER_BG}; border-radius:12px; padding:'
            f'1rem; font-weight:600; font-size:0.95rem;">'
            f'This booking was cancelled. Please contact the shop for '
            f'details.</div>'
        )

    steps = ["Booked", "In Progress", "Ready", "Delivered"]
    cur = _STATUS_TO_TIMELINE_INDEX.get(current_status, 0)

    parts: list[str] = []
    for i, label in enumerate(steps):
        is_done = i <= cur
        is_active = (i == cur)
        if is_done:
            bg, border, fg = PRIMARY, PRIMARY, "#FFFFFF"
            glyph = "●"
        else:
            bg, border, fg = SURFACE, BORDER_STRONG, "#CBD5E1"
            glyph = "○"
        text_color = INK if is_done else MUTED
        text_weight = 700 if is_active else 600 if is_done else 500
        parts.append(
            f'<div style="display:flex; flex-direction:column; '
            f'align-items:center; flex:1;">'
            f'<div style="width:30px; height:30px; border-radius:50%; '
            f'background:{bg}; border:2px solid {border}; color:{fg}; '
            f'display:inline-flex; align-items:center; justify-content:'
            f'center; font-size:0.7rem; line-height:1;">{glyph}</div>'
            f'<div style="font-size:0.78rem; font-weight:{text_weight}; '
            f'color:{text_color}; text-align:center; margin-top:0.4rem;">'
            f'{label}</div>'
            f'</div>'
        )
        if i < len(steps) - 1:
            connector = PRIMARY if i < cur else BORDER
            parts.append(
                f'<div style="flex:0.7; height:2px; background:{connector}; '
                f'margin-top:0.95rem;"></div>'
            )
    return (
        f'<div style="display:flex; align-items:flex-start; '
        f'background:{SURFACE}; border:1px solid {BORDER}; border-radius:'
        f'12px; padding:1.2rem 1rem;">{"".join(parts)}</div>'
    )


# ── Success token card (booking confirmation) ──────────────────────────────
def success_token_card(token: str, total_fee: int, eta_hours: int,
                       extra_note: str = "") -> str:
    extra = (
        f'<div style="margin-top:0.8rem; color:{SUCCESS_TEXT}; font-size:'
        f'0.88rem;">{extra_note}</div>'
    ) if extra_note else ""
    return (
        f'<div style="background:{SUCCESS_BG}; border:1px solid {SUCCESS}; '
        f'border-radius:12px; padding:1.4rem; box-shadow:0 1px 3px '
        f'rgba(22,163,74,0.10);">'
        f'<div style="font-size:0.74rem; font-weight:700; color:{SUCCESS_TEXT}; '
        f'text-transform:uppercase; letter-spacing:0.08em;">'
        f'Booking confirmed</div>'
        f'<div class="c2s-token" style="margin-top:0.4rem;">{token}</div>'
        f'<div style="color:{SUCCESS_TEXT}; font-size:0.9rem; margin-top:'
        f'0.6rem;">Save this token to track your booking.</div>'
        f'<div style="display:flex; gap:1.2rem; margin-top:0.9rem; '
        f'color:{INK}; font-size:0.92rem;">'
        f'<div><b>Total</b> ₹{total_fee}</div>'
        f'<div><b>Ready in</b> ~{eta_hours}h</div>'
        f'</div>{extra}'
        f'</div>'
    )


# ── Backwards-compat shims (older pages) ───────────────────────────────────
# These signatures used to render heavier editorial helpers; we keep the
# names so any leftover callers don't break, and render them in the new style.

def hero(*, badge: str, title_html: str, subtitle: str) -> None:
    section_header(eyebrow=badge, title=title_html, subtitle=subtitle)


def stat_strip(stats: list[tuple[str, str]]) -> None:
    cols = st.columns(len(stats) or 1)
    for col, (value, label) in zip(cols, stats):
        with col:
            st.markdown(
                kpi_card("●", str(value), label, PRIMARY),
                unsafe_allow_html=True,
            )


def feature_card(num: str, icon: str, title: str, text: str) -> None:
    st.markdown(
        f'<div style="background:{SURFACE}; border:1px solid {BORDER}; '
        f'border-radius:12px; padding:1.2rem;">'
        f'<div style="font-size:1.4rem;">{icon}</div>'
        f'<div style="font-weight:700; font-size:1rem; margin-top:0.5rem; '
        f'color:{INK};">{title}</div>'
        f'<div style="color:{MUTED}; font-size:0.88rem; margin-top:0.4rem; '
        f'line-height:1.5;">{text}</div></div>',
        unsafe_allow_html=True,
    )


def how_step(num: int, title: str, text: str) -> None:
    st.markdown(
        f'<div style="background:{SURFACE}; border:1px solid {BORDER}; '
        f'border-radius:12px; padding:1.2rem;">'
        f'<div style="display:inline-flex; align-items:center; '
        f'justify-content:center; width:30px; height:30px; border-radius:'
        f'50%; background:{PRIMARY_TINT}; color:{PRIMARY_DARK}; '
        f'font-weight:700; font-size:0.85rem;">{num}</div>'
        f'<div style="font-weight:700; font-size:1rem; margin-top:0.6rem; '
        f'color:{INK};">{title}</div>'
        f'<div style="color:{MUTED}; font-size:0.88rem; margin-top:0.4rem; '
        f'line-height:1.5;">{text}</div></div>',
        unsafe_allow_html=True,
    )


def cta_banner(eyebrow: str, title_html: str, subtitle: str) -> None:
    st.markdown(
        f'<div style="background:linear-gradient(135deg, {PRIMARY} 0%, '
        f'{PRIMARY_DARK} 100%); border-radius:12px; padding:1.6rem 1.2rem; '
        f'color:#FFFFFF; margin:1.6rem 0;">'
        f'<div style="font-size:0.74rem; font-weight:700; text-transform:'
        f'uppercase; letter-spacing:0.08em; opacity:0.85;">{eyebrow}</div>'
        f'<h2 style="color:#FFFFFF !important; font-size:1.4rem !important; '
        f'font-weight:700 !important; margin:0.4rem 0 0.4rem !important;">'
        f'{title_html}</h2>'
        f'<div style="opacity:0.9; font-size:0.95rem;">{subtitle}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )
