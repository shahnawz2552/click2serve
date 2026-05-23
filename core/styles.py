"""Editorial brand stylesheet for Click2Serve.

Inspired by ventriloc.ca and similar premium Quebec data-agency landing
pages: cream paper background, near-black ink, a single bright lime
accent, and confident editorial typography on an asymmetric grid.

Public surface:
    inject_global_css() — drop the stylesheet into the current page once
    hero(...)            — editorial hero with optional lime-highlight word
    stat_strip(...)      — big-number stats row with horizontal rules
    section_header(...)  — eyebrow + title + subtitle pattern
    feature_card(...)    — clean numbered card
    how_step(...)        — editorial step block with big numeral
    cta_banner(...)      — black banner footer with lime headline
"""
from __future__ import annotations

import streamlit as st

# ── Brand palette ───────────────────────────────────────────────────────────
INK = "#0E120F"          # near-black with a green undertone
INK_SOFT = "#1F2620"
PAPER = "#F1ECE0"        # warm cream
PAPER_SOFT = "#F8F4EA"
SURFACE = "#FFFFFF"
LIME = "#C7F284"         # the signature accent
LIME_DEEP = "#9FC95D"
MUTED = "#5A6157"
RULE = "#1F2620"


_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&family=Instrument+Serif:ital@0;1&display=swap');

/* ── Global background + base type ─────────────────────────────────── */
html, body, [data-testid="stAppViewContainer"], .stApp {{
    background: {PAPER} !important;
    color: {INK} !important;
}}
html, body, [class*="css"], [class*="st-"] {{
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    color: {INK};
    -webkit-font-smoothing: antialiased;
}}

h1, h2, h3, h4, h5, h6 {{
    font-family: 'Inter', system-ui, sans-serif !important;
    font-weight: 800 !important;
    letter-spacing: -0.035em;
    color: {INK} !important;
    line-height: 1.05 !important;
}}
h1 {{ font-size: 3rem !important; }}
h2 {{ font-size: 2.2rem !important; }}
h3 {{ font-size: 1.4rem !important; letter-spacing: -0.02em; }}

p, span, label, div {{ color: {INK}; }}

/* Tighten Streamlit's default page padding */
section.main > div.block-container {{
    padding-top: 1.4rem;
    padding-bottom: 4rem;
    max-width: 1180px;
}}

/* ── Editorial HERO ────────────────────────────────────────────────── */
.c2s-hero {{
    background: {PAPER};
    border-top: 1px solid {RULE};
    border-bottom: 1px solid {RULE};
    padding: 3.6rem 0 3rem;
    margin-bottom: 2.4rem;
}}
.c2s-hero-eyebrow {{
    display: flex;
    align-items: center;
    gap: 0.6rem;
    font-size: 0.78rem;
    font-weight: 600;
    color: {INK};
    text-transform: uppercase;
    letter-spacing: 0.16em;
    margin-bottom: 1.6rem;
}}
.c2s-hero-eyebrow::before {{
    content: '';
    width: 10px; height: 10px;
    background: {LIME};
    border-radius: 50%;
}}
.c2s-hero-title {{
    font-size: clamp(2.4rem, 6vw, 4.6rem) !important;
    font-weight: 900 !important;
    line-height: 0.98 !important;
    letter-spacing: -0.04em;
    margin: 0 0 1.4rem !important;
    max-width: 920px;
    color: {INK} !important;
}}
.c2s-accent {{
    display: inline-block;
    background: linear-gradient(180deg, transparent 60%, {LIME} 60%, {LIME} 96%, transparent 96%);
    padding: 0 0.15em;
}}
.c2s-italic {{
    font-family: 'Instrument Serif', Georgia, serif !important;
    font-style: italic;
    font-weight: 400 !important;
    letter-spacing: -0.01em;
}}
.c2s-hero-sub {{
    font-size: 1.15rem;
    color: {MUTED};
    max-width: 640px;
    margin: 0 0 1.6rem;
    line-height: 1.55;
}}

/* ── BIG-NUMBER stat strip ─────────────────────────────────────────── */
.c2s-stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
    margin: 0 0 2.4rem;
    border-top: 1px solid {RULE};
    border-bottom: 1px solid {RULE};
}}
.c2s-stat {{
    padding: 1.4rem 1.2rem;
    border-right: 1px solid {RULE};
}}
.c2s-stat:last-child {{ border-right: none; }}
.c2s-stat-value {{
    font-size: 2.6rem;
    font-weight: 900;
    color: {INK};
    line-height: 1;
    letter-spacing: -0.04em;
    margin-bottom: 0.3rem;
}}
.c2s-stat-label {{
    font-size: 0.74rem;
    color: {MUTED};
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.12em;
}}
.c2s-stat-value sup {{
    font-size: 1rem;
    color: {LIME_DEEP};
    margin-left: 0.15em;
    vertical-align: top;
}}

/* ── Editorial section header ──────────────────────────────────────── */
.c2s-eyebrow {{
    display: inline-flex;
    align-items: center;
    gap: 0.55rem;
    font-size: 0.74rem;
    font-weight: 600;
    color: {INK};
    text-transform: uppercase;
    letter-spacing: 0.16em;
    margin-bottom: 0.9rem;
}}
.c2s-eyebrow::before {{
    content: '';
    width: 28px; height: 1px;
    background: {INK};
}}
.c2s-section-title {{
    font-size: clamp(1.8rem, 3.5vw, 2.6rem) !important;
    font-weight: 900 !important;
    letter-spacing: -0.035em;
    line-height: 1.05 !important;
    margin-bottom: 0.6rem;
    max-width: 880px;
}}
.c2s-section-sub {{
    color: {MUTED};
    font-size: 1.05rem;
    max-width: 660px;
    margin-bottom: 1.6rem;
    line-height: 1.55;
}}

/* ── Cards (st.container border + custom HTML) ─────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 0 !important;
    border: 1px solid {RULE} !important;
    background: {SURFACE};
    transition: background 0.18s ease, transform 0.18s ease;
}}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    background: {PAPER_SOFT};
}}

/* ── Buttons (editorial: square corners, sharp hover) ──────────────── */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    border-radius: 0 !important;
    font-weight: 600 !important;
    padding: 0.7rem 1.3rem !important;
    border: 1px solid {INK} !important;
    background: {SURFACE} !important;
    color: {INK} !important;
    transition: background 0.15s ease, color 0.15s ease;
    font-size: 0.94rem !important;
    letter-spacing: -0.005em;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
    background: {INK} !important;
    color: {PAPER} !important;
    border-color: {INK} !important;
}}

/* Primary buttons get the lime accent on hover */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {{
    background: {INK} !important;
    color: {PAPER} !important;
    border: 1px solid {INK} !important;
}}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {{
    background: {LIME} !important;
    color: {INK} !important;
    border-color: {LIME} !important;
}}
.stButton > button[kind="primary"]:disabled {{
    opacity: 0.45;
}}

/* Page links (sidebar nav and inline) — minimal underline-on-hover */
a[data-testid="stPageLink-NavLink"] {{
    border-radius: 0 !important;
    font-weight: 500;
}}
a[data-testid="stPageLink-NavLink"]:hover {{
    background: {LIME} !important;
    color: {INK} !important;
}}

/* ── Metrics — big editorial numbers ───────────────────────────────── */
[data-testid="stMetric"] {{
    background: {SURFACE};
    border: 1px solid {RULE};
    border-radius: 0;
    padding: 1.2rem 1.2rem;
}}
[data-testid="stMetricValue"] {{
    font-size: 2rem !important;
    font-weight: 900 !important;
    color: {INK} !important;
    letter-spacing: -0.03em;
}}
[data-testid="stMetricLabel"] {{
    color: {MUTED} !important;
    font-weight: 600 !important;
    text-transform: uppercase;
    letter-spacing: 0.10em;
    font-size: 0.72rem !important;
}}

/* ── Inputs — squared, editorial ───────────────────────────────────── */
input, textarea, .stTextInput > div > div > input, .stNumberInput input {{
    border-radius: 4px !important;
}}
.stTextInput > div > div, .stNumberInput > div, .stSelectbox > div > div,
.stDateInput > div > div, .stTextArea > div > div {{
    border-radius: 4px !important;
    border-color: {RULE} !important;
}}

/* ── Sidebar — paper background, sharp rule on the right ───────────── */
section[data-testid="stSidebar"] {{
    background: {PAPER} !important;
    border-right: 1px solid {RULE};
}}

/* ── Alerts — flat, editorial ──────────────────────────────────────── */
[data-testid="stAlert"] {{
    border-radius: 0 !important;
    border-left: 4px solid {INK} !important;
    background: {SURFACE} !important;
}}

/* ── Feature card (HTML helper) ────────────────────────────────────── */
.c2s-feature {{
    background: {SURFACE};
    border: 1px solid {RULE};
    padding: 1.8rem 1.5rem 1.6rem;
    height: 100%;
    transition: transform 0.18s ease;
}}
.c2s-feature:hover {{ transform: translateY(-3px); }}
.c2s-feature-marker {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 1.2rem;
}}
.c2s-feature-num {{
    font-family: 'Instrument Serif', serif;
    font-size: 1.4rem;
    color: {MUTED};
    font-weight: 400;
    font-style: italic;
}}
.c2s-feature-icon {{
    width: 38px; height: 38px;
    border-radius: 999px;
    background: {LIME};
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 1.1rem;
}}
.c2s-feature-title {{
    font-size: 1.25rem;
    font-weight: 800;
    margin-bottom: 0.45rem;
    color: {INK};
    letter-spacing: -0.02em;
    line-height: 1.2;
}}
.c2s-feature-text {{
    color: {MUTED};
    font-size: 0.95rem;
    line-height: 1.55;
}}

/* ── How-it-works step ─────────────────────────────────────────────── */
.c2s-step {{
    border-top: 1px solid {RULE};
    padding: 1.8rem 0 1.5rem;
    height: 100%;
    display: flex;
    flex-direction: column;
}}
.c2s-step-num {{
    font-size: 0.78rem;
    font-weight: 600;
    color: {INK};
    text-transform: uppercase;
    letter-spacing: 0.12em;
    margin-bottom: 1rem;
}}
.c2s-step-num-num {{
    color: {LIME_DEEP};
    margin-right: 0.4rem;
    font-family: 'Instrument Serif', serif;
    font-size: 1.5rem;
    font-style: italic;
    font-weight: 400;
    vertical-align: -2px;
}}
.c2s-step h4 {{
    font-size: 1.3rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
    margin: 0 0 0.5rem !important;
}}
.c2s-step p {{
    color: {MUTED};
    font-size: 0.96rem;
    line-height: 1.55;
    margin-bottom: 0;
}}

/* ── CTA banner (closing footer) ───────────────────────────────────── */
.c2s-cta-banner {{
    background: {INK};
    color: {PAPER};
    padding: 3.5rem 2.4rem;
    margin-top: 3rem;
    margin-bottom: 1rem;
    border: 1px solid {INK};
}}
.c2s-cta-banner-eyebrow {{
    font-size: 0.74rem;
    font-weight: 600;
    color: {LIME};
    text-transform: uppercase;
    letter-spacing: 0.16em;
    margin-bottom: 0.9rem;
}}
.c2s-cta-banner h2 {{
    color: {PAPER} !important;
    font-size: clamp(1.8rem, 4vw, 2.8rem) !important;
    font-weight: 900 !important;
    letter-spacing: -0.035em;
    line-height: 1.05 !important;
    margin: 0 0 0.8rem !important;
    max-width: 760px;
}}
.c2s-cta-banner h2 .c2s-accent {{
    background: linear-gradient(180deg, transparent 62%, {LIME} 62%, {LIME} 95%, transparent 95%);
    color: {INK};
    padding: 0 0.18em;
}}
.c2s-cta-banner p {{
    color: rgba(241, 236, 224, 0.78);
    font-size: 1.05rem;
    margin: 0 0 1.4rem;
    max-width: 580px;
    line-height: 1.55;
}}

/* Service-card pieces */
.c2s-cat {{
    font-size: 0.7rem;
    font-weight: 600;
    color: {MUTED};
    text-transform: uppercase;
    letter-spacing: 0.14em;
    margin-bottom: 0.6rem;
}}
.c2s-svc-name {{
    font-size: 1.15rem;
    font-weight: 800;
    color: {INK};
    margin-bottom: 0.4rem;
    line-height: 1.25;
    letter-spacing: -0.02em;
}}
.c2s-svc-desc {{
    color: {MUTED};
    font-size: 0.92rem;
    line-height: 1.5;
    min-height: 60px;
    margin-bottom: 0.8rem;
}}
.c2s-meta-row {{
    display: flex;
    gap: 1rem;
    margin: 0.6rem 0 0.5rem;
    padding-top: 0.7rem;
    border-top: 1px dashed {RULE};
}}
.c2s-pill {{
    font-size: 0.86rem;
    font-weight: 700;
    color: {INK};
}}
.c2s-pill .c2s-pill-label {{
    font-weight: 500;
    color: {MUTED};
    margin-right: 0.3rem;
}}

/* Editorial divider */
.c2s-rule {{
    border: 0;
    border-top: 1px solid {RULE};
    margin: 2.5rem 0;
}}

/* Mobile breakpoint */
@media (max-width: 640px) {{
    .c2s-hero {{ padding: 2.6rem 0 2rem; }}
    .c2s-hero-title {{ font-size: 2.2rem !important; }}
    .c2s-stat-value {{ font-size: 2rem; }}
    .c2s-stat {{ border-right: none; border-bottom: 1px solid {RULE}; }}
    .c2s-stat:last-child {{ border-bottom: none; }}
}}
</style>
"""


def inject_global_css() -> None:
    """Drop the brand stylesheet into the current page exactly once."""
    if not st.session_state.get("_c2s_css_injected"):
        st.markdown(_CSS, unsafe_allow_html=True)
        st.session_state["_c2s_css_injected"] = True


# ── Reusable HTML helpers ────────────────────────────────────────────────────

def hero(*, badge: str, title_html: str, subtitle: str) -> None:
    """Editorial hero with eyebrow + giant title + subtitle.
    ``title_html`` may include:
        <span class='c2s-accent'>...</span>   for a lime-highlight word
        <span class='c2s-italic'>...</span>   for an Instrument Serif italic word
    """
    st.markdown(
        f"""
        <div class="c2s-hero">
            <div class="c2s-hero-eyebrow">{badge}</div>
            <h1 class="c2s-hero-title">{title_html}</h1>
            <p class="c2s-hero-sub">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_strip(stats: list[tuple[str, str]]) -> None:
    """Big-number editorial stat strip. ``stats`` is ``[(value, label), …]``."""
    inner = "".join(
        f'<div class="c2s-stat">'
        f'<div class="c2s-stat-value">{v}</div>'
        f'<div class="c2s-stat-label">{l}</div>'
        f'</div>'
        for v, l in stats
    )
    st.markdown(f'<div class="c2s-stats">{inner}</div>', unsafe_allow_html=True)


def section_header(eyebrow: str, title: str, subtitle: str = "") -> None:
    sub = f'<p class="c2s-section-sub">{subtitle}</p>' if subtitle else ""
    st.markdown(
        f"""
        <div style="margin-top: 1.5rem;">
            <span class="c2s-eyebrow">{eyebrow}</span>
            <h2 class="c2s-section-title">{title}</h2>
            {sub}
        </div>
        """,
        unsafe_allow_html=True,
    )


def feature_card(num: str, icon: str, title: str, text: str) -> None:
    """Numbered editorial feature card. ``num`` like '01', ``icon`` an emoji."""
    st.markdown(
        f"""
        <div class="c2s-feature">
            <div class="c2s-feature-marker">
                <span class="c2s-feature-num">{num}</span>
                <span class="c2s-feature-icon">{icon}</span>
            </div>
            <div class="c2s-feature-title">{title}</div>
            <div class="c2s-feature-text">{text}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def how_step(num: int, title: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="c2s-step">
            <div class="c2s-step-num">
                <span class="c2s-step-num-num">{num:02d}</span>
                Step {num}
            </div>
            <h4>{title}</h4>
            <p>{text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def cta_banner(eyebrow: str, title_html: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="c2s-cta-banner">
            <div class="c2s-cta-banner-eyebrow">{eyebrow}</div>
            <h2>{title_html}</h2>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )



# ── Editorial status badge helper ──────────────────────────────────────────
# Renders a small typographic glyph + label, used on track / bookings views.

_STATUS_CONFIG = {
    "Pending":     ("○", MUTED,     "Awaiting start"),
    "In Progress": ("●", LIME_DEEP, "In progress"),
    "Ready":       ("●", INK,       "Ready for pickup"),
    "Delivered":   ("✓", INK,       "Delivered"),
    "Cancelled":   ("×", MUTED,     "Cancelled"),
}


def status_badge(status: str, *, big: bool = False) -> str:
    """Return inline HTML for a flat editorial status badge.

    ``big=True`` is used on the customer track-page where the status is
    the primary thing on the page; ``big=False`` for compact admin lists.
    """
    glyph, color, label = _STATUS_CONFIG.get(status, ("●", INK, status))
    if big:
        return (
            f'<div style="display:inline-flex; align-items:center; '
            f'gap:0.7rem; font-size:1.4rem; font-weight:800; color:{INK}; '
            f'letter-spacing:-0.025em; line-height:1;">'
            f'<span style="color:{color}; font-size:1.4em; line-height:1;">{glyph}</span>'
            f'{label}'
            f'</div>'
        )
    return (
        f'<span style="display:inline-flex; align-items:center; '
        f'gap:0.4rem; font-size:0.9rem; font-weight:600; color:{INK};">'
        f'<span style="color:{color}; font-size:1.05em; line-height:1;">{glyph}</span>'
        f'{status}'
        f'</span>'
    )


_PAYMENT_CONFIG = {
    "verified":    ("●", LIME_DEEP, "Payment verified"),
    "submitted":   ("○", LIME_DEEP, "Awaiting verification"),
    "rejected":    ("×", "#B85C5C", "Payment rejected"),
    "unpaid":      ("○", MUTED,     "Unpaid"),
}


def payment_badge(payment_status: str) -> str:
    """Inline HTML badge for a booking's payment_status."""
    glyph, color, label = _PAYMENT_CONFIG.get(
        payment_status or "unpaid", ("●", INK, payment_status or "")
    )
    return (
        f'<span style="display:inline-flex; align-items:center; '
        f'gap:0.4rem; font-size:0.88rem; font-weight:600; color:{INK};">'
        f'<span style="color:{color}; font-size:1.05em; line-height:1;">{glyph}</span>'
        f'{label}'
        f'</span>'
    )
