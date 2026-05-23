"""Global CSS + reusable HTML helpers for the Click2Serve UI.

The look-and-feel is inspired by clickup.com:
  - Inter font, large bold display sizes
  - Vibrant purple → pink gradients on the hero and primary CTAs
  - Soft glassy cards with 18px radius and subtle shadows
  - Pill badges, gradient text accents, hover lift on buttons

Everything is injected once per page via `inject_global_css()`. Page-level
helpers like `hero()` and `stat_strip()` then write semantic HTML that
picks up these styles.
"""
from __future__ import annotations

import streamlit as st

# ── Brand palette (ClickUp-inspired) ────────────────────────────────────────
PRIMARY = "#7B68EE"      # purple
PRIMARY_DARK = "#5B49C9"
PINK = "#FB3F8C"
SKY = "#06A0F0"
INK = "#0A0E27"
MUTED = "#5C5F7C"
BORDER = "#E7E9F4"
SURFACE = "#FFFFFF"
SURFACE_ALT = "#F7F8FB"

GRADIENT = f"linear-gradient(135deg, {PRIMARY} 0%, {PINK} 100%)"
GRADIENT_SOFT = f"linear-gradient(135deg, #F0EDFF 0%, #FFE9F4 100%)"


_CSS = f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

/* ── Base typography ──────────────────────────────────────────────── */
html, body, [class*="css"], [class*="st-"] {{
    font-family: 'Inter', system-ui, -apple-system, sans-serif !important;
    color: {INK};
}}

h1, h2, h3, h4, h5, h6 {{
    font-family: 'Inter', system-ui, sans-serif !important;
    letter-spacing: -0.02em;
    font-weight: 800 !important;
    color: {INK} !important;
}}

h1 {{ font-size: 2.6rem !important; line-height: 1.1 !important; }}
h2 {{ font-size: 2rem   !important; line-height: 1.2 !important; }}
h3 {{ font-size: 1.4rem !important; line-height: 1.3 !important; }}

p, span, label, div {{ color: {INK}; }}

/* ── Tighten Streamlit's default container padding on the main page ─ */
section.main > div.block-container {{
    padding-top: 1.5rem;
    padding-bottom: 4rem;
    max-width: 1180px;
}}

/* ── Hero ──────────────────────────────────────────────────────────── */
.c2s-hero {{
    position: relative;
    background: {GRADIENT_SOFT};
    border: 1px solid {BORDER};
    border-radius: 28px;
    padding: 3.2rem 2.4rem 3rem;
    margin-bottom: 2rem;
    overflow: hidden;
    text-align: center;
}}
.c2s-hero::before {{
    content: '';
    position: absolute;
    top: -120px; right: -120px;
    width: 320px; height: 320px;
    background: radial-gradient(closest-side, rgba(123,104,238,0.35), transparent 70%);
    z-index: 0;
}}
.c2s-hero::after {{
    content: '';
    position: absolute;
    bottom: -160px; left: -120px;
    width: 360px; height: 360px;
    background: radial-gradient(closest-side, rgba(251,63,140,0.28), transparent 70%);
    z-index: 0;
}}
.c2s-hero > * {{ position: relative; z-index: 1; }}

.c2s-hero-badge {{
    display: inline-block;
    padding: 0.35rem 0.9rem;
    background: white;
    border: 1px solid {BORDER};
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    color: {PRIMARY};
    margin-bottom: 1rem;
    box-shadow: 0 2px 6px rgba(10, 14, 39, 0.04);
}}

.c2s-hero-title {{
    font-size: clamp(2.2rem, 4.6vw, 3.6rem) !important;
    font-weight: 900 !important;
    line-height: 1.05 !important;
    letter-spacing: -0.03em;
    margin: 0 auto 1rem !important;
    max-width: 780px;
}}

.c2s-gradient-text {{
    background: {GRADIENT};
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
}}

.c2s-hero-sub {{
    font-size: 1.1rem;
    color: {MUTED};
    max-width: 600px;
    margin: 0 auto 1.6rem;
    line-height: 1.55;
}}

/* ── Stat strip (under hero) ──────────────────────────────────────── */
.c2s-stats {{
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
    gap: 1rem;
    background: white;
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 1.2rem 1.4rem;
    margin: -2.4rem auto 2rem;
    max-width: 760px;
    position: relative;
    z-index: 2;
    box-shadow: 0 14px 40px rgba(10, 14, 39, 0.06);
}}
.c2s-stat {{ text-align: center; }}
.c2s-stat-value {{
    font-size: 1.7rem;
    font-weight: 800;
    background: {GRADIENT};
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    line-height: 1.1;
}}
.c2s-stat-label {{
    font-size: 0.78rem;
    color: {MUTED};
    font-weight: 500;
    letter-spacing: 0.02em;
    margin-top: 0.2rem;
}}

/* ── Section headers ──────────────────────────────────────────────── */
.c2s-eyebrow {{
    display: inline-block;
    padding: 0.3rem 0.85rem;
    background: white;
    border: 1px solid {BORDER};
    border-radius: 999px;
    font-size: 0.72rem;
    font-weight: 700;
    color: {PRIMARY};
    text-transform: uppercase;
    letter-spacing: 0.08em;
    margin-bottom: 0.9rem;
}}
.c2s-section-title {{
    font-size: 2rem !important;
    font-weight: 800 !important;
    letter-spacing: -0.02em;
    margin-bottom: 0.4rem;
}}
.c2s-section-sub {{
    color: {MUTED};
    font-size: 1.02rem;
    max-width: 640px;
    margin-bottom: 1.4rem;
}}

/* ── Service cards (grid) ─────────────────────────────────────────── */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    border-radius: 18px !important;
    border-color: {BORDER} !important;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
    background: white;
}}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    transform: translateY(-2px);
    box-shadow: 0 18px 40px rgba(10, 14, 39, 0.07);
    border-color: rgba(123, 104, 238, 0.35) !important;
}}

/* ── Buttons ──────────────────────────────────────────────────────── */
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {{
    border-radius: 12px !important;
    font-weight: 600 !important;
    padding: 0.6rem 1.2rem !important;
    border: 1px solid {BORDER} !important;
    transition: transform 0.15s ease, box-shadow 0.15s ease, background 0.15s ease;
    color: {INK} !important;
    background: white !important;
}}
.stButton > button:hover, .stDownloadButton > button:hover, .stFormSubmitButton > button:hover {{
    transform: translateY(-1px);
    box-shadow: 0 8px 20px rgba(10, 14, 39, 0.08);
    border-color: {PRIMARY} !important;
}}

/* Primary buttons get the brand gradient */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {{
    background: {GRADIENT} !important;
    color: white !important;
    border: none !important;
    box-shadow: 0 6px 18px rgba(123, 104, 238, 0.32);
}}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {{
    transform: translateY(-2px);
    box-shadow: 0 12px 28px rgba(123, 104, 238, 0.42);
    filter: brightness(1.05);
}}
.stButton > button[kind="primary"]:disabled {{
    opacity: 0.55;
    transform: none;
    box-shadow: none;
}}

/* ── Page links (the sidebar nav and inline ones) ─────────────────── */
a[data-testid="stPageLink-NavLink"]:hover {{
    background: rgba(123, 104, 238, 0.08) !important;
    border-radius: 10px;
}}

/* ── Metrics ──────────────────────────────────────────────────────── */
[data-testid="stMetric"] {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 16px;
    padding: 1rem 1.1rem;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}}
[data-testid="stMetric"]:hover {{
    transform: translateY(-2px);
    box-shadow: 0 10px 24px rgba(10, 14, 39, 0.06);
}}
[data-testid="stMetricValue"] {{
    font-size: 1.7rem !important;
    font-weight: 800 !important;
    color: {INK} !important;
}}
[data-testid="stMetricLabel"] {{
    color: {MUTED} !important;
    font-weight: 500 !important;
    text-transform: uppercase;
    letter-spacing: 0.06em;
    font-size: 0.72rem !important;
}}

/* ── Inputs ───────────────────────────────────────────────────────── */
input, textarea, .stTextInput > div > div > input, .stNumberInput input {{
    border-radius: 10px !important;
}}
.stTextInput > div > div, .stNumberInput > div, .stSelectbox > div > div,
.stDateInput > div > div, .stTextArea > div > div {{
    border-radius: 10px !important;
}}

/* ── Sidebar polish ───────────────────────────────────────────────── */
section[data-testid="stSidebar"] {{
    background: linear-gradient(180deg, #FFFFFF 0%, #FAF9FF 100%);
    border-right: 1px solid {BORDER};
}}

/* ── Alerts / info / success / warning ────────────────────────────── */
[data-testid="stAlert"] {{
    border-radius: 14px !important;
    border-left-width: 4px !important;
}}

/* ── Feature card (custom HTML) ───────────────────────────────────── */
.c2s-feature {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 1.6rem 1.4rem;
    height: 100%;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}}
.c2s-feature:hover {{
    transform: translateY(-3px);
    box-shadow: 0 14px 34px rgba(10, 14, 39, 0.07);
}}
.c2s-feature-icon {{
    width: 44px; height: 44px;
    border-radius: 12px;
    background: {GRADIENT_SOFT};
    display: inline-flex; align-items: center; justify-content: center;
    font-size: 1.4rem;
    margin-bottom: 0.9rem;
}}
.c2s-feature-title {{
    font-size: 1.1rem;
    font-weight: 700;
    margin-bottom: 0.3rem;
    color: {INK};
}}
.c2s-feature-text {{
    color: {MUTED};
    font-size: 0.92rem;
    line-height: 1.55;
}}

/* ── How-it-works step ────────────────────────────────────────────── */
.c2s-step {{
    background: white;
    border: 1px solid {BORDER};
    border-radius: 18px;
    padding: 1.6rem 1.4rem;
    height: 100%;
    position: relative;
}}
.c2s-step-num {{
    position: absolute;
    top: -18px; left: 1.4rem;
    width: 38px; height: 38px;
    border-radius: 12px;
    background: {GRADIENT};
    color: white;
    display: flex; align-items: center; justify-content: center;
    font-weight: 800;
    font-size: 1.1rem;
    box-shadow: 0 8px 18px rgba(123, 104, 238, 0.32);
}}
.c2s-step h4 {{ margin-top: 1.1rem; font-size: 1.1rem !important; font-weight: 700 !important; }}
.c2s-step p  {{ color: {MUTED}; font-size: 0.92rem; line-height: 1.55; margin-bottom: 0; }}

/* ── CTA banner (footer of the home page) ─────────────────────────── */
.c2s-cta-banner {{
    background: {GRADIENT};
    border-radius: 24px;
    padding: 2.6rem 2rem;
    text-align: center;
    color: white;
    margin-top: 2.5rem;
}}
.c2s-cta-banner h2 {{
    color: white !important;
    font-size: 2rem !important;
    margin-bottom: 0.6rem !important;
}}
.c2s-cta-banner p {{
    color: rgba(255,255,255,0.92);
    font-size: 1.05rem;
    margin-bottom: 0;
}}

/* ── Service price + ETA mini badges ──────────────────────────────── */
.c2s-meta-row {{
    display: flex;
    gap: 0.55rem;
    margin: 0.55rem 0 0.4rem;
}}
.c2s-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    padding: 0.22rem 0.6rem;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
}}
.c2s-pill-price {{
    background: rgba(123,104,238,0.10);
    color: {PRIMARY_DARK};
}}
.c2s-pill-eta {{
    background: rgba(251,63,140,0.10);
    color: {PINK};
}}
.c2s-cat {{
    font-size: 0.74rem;
    font-weight: 600;
    color: {MUTED};
    text-transform: uppercase;
    letter-spacing: 0.06em;
    margin-bottom: 0.35rem;
}}

/* Keep things responsive on small screens */
@media (max-width: 640px) {{
    .c2s-hero {{ padding: 2.2rem 1.2rem; border-radius: 22px; }}
    .c2s-hero-title {{ font-size: 2rem !important; }}
    .c2s-stats {{ margin-top: -1.5rem; padding: 0.9rem 1rem; }}
}}
</style>
"""


def inject_global_css() -> None:
    """Drop the brand stylesheet into the current page exactly once."""
    if not st.session_state.get("_c2s_css_injected"):
        st.markdown(_CSS, unsafe_allow_html=True)
        st.session_state["_c2s_css_injected"] = True


# ── Reusable HTML fragments ─────────────────────────────────────────────────

def hero(*, badge: str, title_html: str, subtitle: str) -> None:
    """Render the gradient hero block. ``title_html`` may include a
    ``<span class='c2s-gradient-text'>...</span>`` fragment for accent."""
    st.markdown(
        f"""
        <div class="c2s-hero">
            <span class="c2s-hero-badge">{badge}</span>
            <h1 class="c2s-hero-title">{title_html}</h1>
            <p class="c2s-hero-sub">{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def stat_strip(stats: list[tuple[str, str]]) -> None:
    """Render the floating stats strip used directly under the hero.

    ``stats`` is a list of (value, label) tuples, e.g. ``[("12+", "Services")]``.
    """
    inner = "".join(
        f'<div class="c2s-stat"><div class="c2s-stat-value">{v}</div>'
        f'<div class="c2s-stat-label">{l}</div></div>'
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


def feature_card(icon: str, title: str, text: str) -> None:
    st.markdown(
        f"""
        <div class="c2s-feature">
            <div class="c2s-feature-icon">{icon}</div>
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
            <div class="c2s-step-num">{num}</div>
            <h4>{title}</h4>
            <p>{text}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )


def cta_banner(title: str, subtitle: str) -> None:
    st.markdown(
        f"""
        <div class="c2s-cta-banner">
            <h2>{title}</h2>
            <p>{subtitle}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
