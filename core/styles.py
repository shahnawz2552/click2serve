"""Global stylesheet + reusable HTML helpers for Click2Serve.

Mobile-first consumer-app aesthetic. The visual language has three layers:

1. Foundation — Inter type, slate ink, blue primary, white surfaces.
2. Energy    — a single warm-amber accent used sparingly to draw the eye
               (hero highlight word, primary CTA glow, "live" stat dots).
3. Motion    — soft fade-ins on page load, hover lifts on cards, smooth
               150-300ms transitions on every interactive element.

Public surface used by pages:
    inject_global_css()         — drop the CSS into the current page once
    section_header(...)         — page-title block (eyebrow + h1 + subtitle)
    hero_block(...)             — big gradient hero used on home (NEW)
    stat_strip([...])           — animated 3-up stat row (NEW)
    category_badge(category)    — colored pill for a service category
    status_badge(status)        — colored pill for a booking status
    payment_badge(state)        — colored pill for payment status
    trust_badge(icon, label)    — small white card used in the home hero row
    progress_steps(steps, cur)  — step bar (used on the booking page)
    status_timeline(status)     — Booked → ... → Delivered timeline
    kpi_card(icon, value, ...)  — dashboard KPI tile with colored icon
    success_token_card(token)   — large green success card with the token
    category_accent(category)   — single hex code for a category (NEW)

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

# Warm-amber accent — used VERY sparingly to draw the eye.
ACCENT = "#F59E0B"
ACCENT_DARK = "#D97706"
ACCENT_TINT = "#FEF3C7"

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
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700;800;900&display=swap');

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
    border-radius: 14px !important;
    padding: 1.05rem !important;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    transition: box-shadow 0.18s ease, border-color 0.18s ease,
                transform 0.18s ease;
}}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
    border-color: {BORDER_STRONG} !important;
    transform: translateY(-2px);
}}

/* ── Buttons — full-width on mobile, 8px radius, no uppercase ───── */
.stButton > button,
.stDownloadButton > button,
.stFormSubmitButton > button,
.stLinkButton > a {{
    width: 100%;
    border-radius: 10px !important;
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
.stFormSubmitButton > button:hover,
.stLinkButton > a:hover {{
    background: {GRAY_BG} !important;
    border-color: {BORDER_STRONG} !important;
    transform: translateY(-1px);
}}

/* Primary buttons — solid blue with subtle warm glow on hover */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {{
    background: linear-gradient(180deg, {PRIMARY} 0%, {PRIMARY_DARK} 100%) !important;
    color: #FFFFFF !important;
    border: 1px solid {PRIMARY_DARK} !important;
    box-shadow:
        0 1px 2px rgba(37, 99, 235, 0.18),
        0 4px 12px rgba(37, 99, 235, 0.12);
}}
.stButton > button[kind="primary"]:hover,
.stFormSubmitButton > button[kind="primary"]:hover,
.stDownloadButton > button[kind="primary"]:hover {{
    background: linear-gradient(180deg, {PRIMARY_DARK} 0%, #1E40AF 100%) !important;
    border-color: #1E3A8A !important;
    box-shadow:
        0 2px 4px rgba(37, 99, 235, 0.30),
        0 12px 24px rgba(37, 99, 235, 0.18);
    transform: translateY(-1px);
}}
.stButton > button[kind="primary"]:disabled {{
    opacity: 0.55;
    box-shadow: none;
    transform: none;
}}

/* ── Page links (sidebar nav + inline) ─────────────────────────── */
a[data-testid="stPageLink-NavLink"] {{
    border-radius: 10px !important;
    font-weight: 500;
    min-height: 40px;
    transition: all 0.15s ease;
}}
a[data-testid="stPageLink-NavLink"]:hover {{
    background: {PRIMARY_TINT} !important;
    color: {PRIMARY_DARK} !important;
    transform: translateX(2px);
}}

/* ── Inputs ─────────────────────────────────────────────────────── */
input, textarea, .stTextInput input, .stNumberInput input {{
    border-radius: 10px !important;
    font-size: 0.92rem !important;
    min-height: 40px;
}}
.stTextInput > div > div,
.stNumberInput > div,
.stSelectbox > div > div,
.stDateInput > div > div,
.stTextArea > div > div {{
    border-radius: 10px !important;
    border-color: {BORDER} !important;
    background: {SURFACE};
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
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
    border-radius: 14px;
    padding: 1rem;
    box-shadow: 0 1px 2px rgba(15, 23, 42, 0.04);
    transition: all 0.15s ease;
}}
[data-testid="stMetric"]:hover {{
    box-shadow: 0 4px 12px rgba(15, 23, 42, 0.06);
    transform: translateY(-1px);
}}
[data-testid="stMetricValue"] {{
    font-size: 1.7rem !important;
    font-weight: 800 !important;
    color: {INK} !important;
    letter-spacing: -0.025em;
}}
[data-testid="stMetricLabel"] {{
    color: {MUTED} !important;
    font-weight: 600 !important;
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
.c2s-page-head {{
    margin-bottom: 1.2rem;
    animation: c2sFadeUp 0.5s ease both;
}}
.c2s-eyebrow {{
    display: inline-flex;
    align-items: center;
    gap: 0.45rem;
    font-size: 0.74rem;
    font-weight: 700;
    color: {PRIMARY};
    text-transform: uppercase;
    letter-spacing: 0.1em;
    margin-bottom: 0.45rem;
}}
.c2s-eyebrow::before {{
    content: "";
    width: 18px;
    height: 2px;
    background: {PRIMARY};
    border-radius: 2px;
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
    font-size: 1.25rem;
    font-weight: 800;
    color: {PRIMARY};
    letter-spacing: -0.02em;
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

/* ──────────────────────────────────────────────────────────────── */
/* Hero & impact elements (NEW)                                     */
/* ──────────────────────────────────────────────────────────────── */

/* Animated soft-aurora gradient — sits behind the hero. */
.c2s-hero {{
    position: relative;
    padding: 2.4rem 1.4rem 2rem;
    margin: 0 -0.4rem 1.6rem;
    border-radius: 22px;
    overflow: hidden;
    background:
        radial-gradient(80% 120% at 20% 10%,  rgba(37, 99, 235, 0.18) 0%, transparent 60%),
        radial-gradient(60% 80% at 100% 0%,  rgba(245, 158, 11, 0.16) 0%, transparent 60%),
        radial-gradient(80% 120% at 80% 100%, rgba(99, 102, 241, 0.16) 0%, transparent 60%),
        linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%);
    border: 1px solid {BORDER};
    animation: c2sFadeUp 0.6s ease both;
}}
.c2s-hero::before {{
    /* subtle dot grid texture */
    content: "";
    position: absolute; inset: 0;
    background-image:
        radial-gradient(circle, rgba(15, 23, 42, 0.05) 1px, transparent 1px);
    background-size: 22px 22px;
    pointer-events: none;
    opacity: 0.55;
}}
.c2s-hero-eyebrow {{
    display: inline-flex; align-items: center; gap: 0.45rem;
    font-size: 0.74rem; font-weight: 700;
    text-transform: uppercase; letter-spacing: 0.14em;
    color: {PRIMARY};
    background: rgba(37, 99, 235, 0.08);
    border: 1px solid rgba(37, 99, 235, 0.18);
    padding: 0.32rem 0.7rem;
    border-radius: 999px;
    position: relative; z-index: 1;
}}
.c2s-hero-eyebrow .dot {{
    width: 7px; height: 7px; border-radius: 50%;
    background: {ACCENT};
    box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.6);
    animation: c2sPulse 1.8s ease-out infinite;
}}
.c2s-hero h1.c2s-hero-title {{
    position: relative; z-index: 1;
    font-size: 2.4rem !important;
    font-weight: 900 !important;
    line-height: 1.05 !important;
    letter-spacing: -0.035em;
    color: {INK} !important;
    margin: 0.9rem 0 0.7rem !important;
    max-width: 22ch;
}}
.c2s-hero-title .accent {{
    background: linear-gradient(120deg, {PRIMARY} 0%, #6366F1 50%, {ACCENT_DARK} 100%);
    -webkit-background-clip: text;
    background-clip: text;
    color: transparent;
}}
.c2s-hero-sub {{
    position: relative; z-index: 1;
    color: {MUTED};
    font-size: 1.02rem;
    line-height: 1.6;
    margin: 0 0 1.2rem;
    max-width: 52ch;
}}

/* Stat strip used right under hero — "12 services · 24h ETA · 100% UPI". */
.c2s-stat-strip {{
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 0.6rem;
    margin: 0.4rem 0 0;
    position: relative; z-index: 1;
}}
.c2s-stat {{
    background: rgba(255, 255, 255, 0.7);
    backdrop-filter: blur(6px);
    -webkit-backdrop-filter: blur(6px);
    border: 1px solid {BORDER};
    border-radius: 12px;
    padding: 0.7rem 0.8rem;
    text-align: center;
    transition: transform 0.18s ease, box-shadow 0.18s ease;
}}
.c2s-stat:hover {{
    transform: translateY(-2px);
    box-shadow: 0 8px 20px rgba(15, 23, 42, 0.06);
}}
.c2s-stat-value {{
    font-size: 1.4rem;
    font-weight: 800;
    color: {INK};
    line-height: 1;
    letter-spacing: -0.025em;
}}
.c2s-stat-value .unit {{
    color: {ACCENT_DARK};
}}
.c2s-stat-label {{
    margin-top: 0.3rem;
    font-size: 0.72rem;
    font-weight: 600;
    color: {MUTED};
    text-transform: uppercase;
    letter-spacing: 0.07em;
}}

/* ──────────────────────────────────────────────────────────────── */
/* Service cards (new styling for the home grid)                    */
/* ──────────────────────────────────────────────────────────────── */
.c2s-service-card {{
    position: relative;
}}
.c2s-service-card .accent-bar {{
    position: absolute; left: 0; right: 0; top: 0;
    height: 4px;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
}}

/* ──────────────────────────────────────────────────────────────── */
/* Animations                                                        */
/* ──────────────────────────────────────────────────────────────── */
@keyframes c2sFadeUp {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
}}
@keyframes c2sPulse {{
    0%   {{ box-shadow: 0 0 0 0 rgba(245, 158, 11, 0.55); }}
    70%  {{ box-shadow: 0 0 0 8px rgba(245, 158, 11, 0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(245, 158, 11, 0); }}
}}

/* Stagger fade-in for grid items */
.c2s-fade-in {{ animation: c2sFadeUp 0.45s ease both; }}

/* ────────────────────────────────────────────────────────────────── */
/*  3D + DYNAMIC LAYER (added in style/3d-dynamic-upgrade)           */
/*  Pure CSS, zero JS deps. All effects respect prefers-reduced-     */
/*  motion via the global @media query at the bottom of this block. */
/* ────────────────────────────────────────────────────────────────── */

/* 1. Animated mesh-gradient backdrop on the hero ─────────────────── */
.c2s-hero {{
    /* Override the static gradient from the base block above. */
    background:
        radial-gradient(at 20% 10%,  rgba(37, 99, 235, 0.22) 0%, transparent 50%),
        radial-gradient(at 100% 0%,  rgba(245, 158, 11, 0.20) 0%, transparent 50%),
        radial-gradient(at 80% 100%, rgba(99, 102, 241, 0.20) 0%, transparent 50%),
        radial-gradient(at 0% 100%,  rgba(16, 185, 129, 0.14) 0%, transparent 55%),
        linear-gradient(135deg, #FFFFFF 0%, #F8FAFC 100%);
    background-size: 200% 200%;
    animation: c2sMeshDrift 14s ease-in-out infinite alternate;
}}
@keyframes c2sMeshDrift {{
    0%   {{ background-position: 0% 50%; }}
    50%  {{ background-position: 100% 50%; }}
    100% {{ background-position: 0% 50%; }}
}}

/* 2. Floating sheen + subtle parallax pulse on the hero ──────────── */
.c2s-hero::after {{
    content: "";
    position: absolute;
    top: -40%; left: -20%;
    width: 60%; height: 200%;
    background: linear-gradient(
        110deg,
        transparent 30%,
        rgba(255, 255, 255, 0.6) 50%,
        transparent 70%
    );
    transform: rotate(20deg);
    animation: c2sSheen 9s ease-in-out infinite;
    pointer-events: none;
    opacity: 0.25;
}}
@keyframes c2sSheen {{
    0%, 100% {{ transform: translateX(-30%) rotate(20deg); }}
    50%      {{ transform: translateX(180%) rotate(20deg); }}
}}

/* 3. 3D tilt on cards ─────────────────────────────────────────────── */
/* Service-card containers and KPI tiles tip very slightly toward the
   cursor on hover. ``perspective`` is on the parent so individual
   children rotate convincingly. */
div[data-testid="stVerticalBlockBorderWrapper"] {{
    transform-style: preserve-3d;
    perspective: 900px;
    will-change: transform, box-shadow;
}}
div[data-testid="stVerticalBlockBorderWrapper"]:hover {{
    transform:
        translateY(-3px)
        rotateX(1.5deg)
        rotateY(-1.5deg)
        scale(1.012);
    box-shadow:
        0 20px 40px -16px rgba(15, 23, 42, 0.12),
        0 8px 20px rgba(15, 23, 42, 0.06);
}}

/* 4. Glassmorphic stat tiles on the hero ─────────────────────────── */
.c2s-stat {{
    background: rgba(255, 255, 255, 0.55);
    border: 1px solid rgba(255, 255, 255, 0.65);
    backdrop-filter: blur(14px) saturate(140%);
    -webkit-backdrop-filter: blur(14px) saturate(140%);
    box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.7),
        0 4px 16px rgba(15, 23, 42, 0.04);
    transform: translateZ(0);
    transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1),
                box-shadow 0.25s ease;
}}
.c2s-stat:hover {{
    transform: translateY(-4px) scale(1.04);
    box-shadow:
        inset 0 1px 0 rgba(255, 255, 255, 0.7),
        0 14px 28px -8px rgba(15, 23, 42, 0.18);
}}

/* 5. Shimmer sweep on primary buttons ─────────────────────────────── */
.stButton > button[kind="primary"],
.stFormSubmitButton > button[kind="primary"],
.stDownloadButton > button[kind="primary"] {{
    position: relative;
    overflow: hidden;
    isolation: isolate;
}}
.stButton > button[kind="primary"]::after,
.stFormSubmitButton > button[kind="primary"]::after,
.stDownloadButton > button[kind="primary"]::after {{
    content: "";
    position: absolute;
    inset: 0;
    background: linear-gradient(
        110deg,
        transparent 35%,
        rgba(255, 255, 255, 0.45) 50%,
        transparent 65%
    );
    transform: translateX(-110%);
    transition: transform 0.65s ease;
    pointer-events: none;
}}
.stButton > button[kind="primary"]:hover::after,
.stFormSubmitButton > button[kind="primary"]:hover::after,
.stDownloadButton > button[kind="primary"]:hover::after {{
    transform: translateX(110%);
}}

/* 6. Pulsing ring + slight bob on the hero pulse-dot ─────────────── */
.c2s-hero-eyebrow .dot {{
    /* Replaces the simpler keyframe in the base block. */
    animation: c2sPulse 1.6s ease-out infinite, c2sBob 3.2s ease-in-out infinite;
}}
@keyframes c2sBob {{
    0%, 100% {{ transform: translateY(0); }}
    50%      {{ transform: translateY(-1px); }}
}}

/* 7. Animated underline on H2s when they enter the viewport ──────── */
h2 {{
    position: relative;
    display: inline-block;
    padding-bottom: 0.18rem;
}}
h2::after {{
    content: "";
    position: absolute;
    left: 0; bottom: 0;
    width: 0;
    height: 2px;
    background: linear-gradient(90deg, {PRIMARY} 0%, {ACCENT} 100%);
    border-radius: 2px;
    transition: width 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}}
.c2s-revealed h2::after,
h2.c2s-revealed::after {{
    width: 100%;
}}

/* 8. Scroll-reveal base + revealed states ─────────────────────────── */
.c2s-reveal {{
    opacity: 0;
    transform: translateY(14px);
    transition: opacity 0.6s ease, transform 0.6s cubic-bezier(0.22, 1, 0.36, 1);
}}
.c2s-revealed.c2s-reveal,
.c2s-revealed .c2s-reveal {{
    opacity: 1;
    transform: translateY(0);
}}

/* 9. Status badges get a subtle pulsing ring when 'live' (Pending /
       In Progress on the bookings detail panel) ─────────────────── */
.c2s-pill[data-live="1"] {{
    box-shadow: 0 0 0 0 currentColor;
    animation: c2sPillPulse 2s ease-out infinite;
}}
@keyframes c2sPillPulse {{
    0%   {{ box-shadow: 0 0 0 0 rgba(37, 99, 235, 0.45); }}
    70%  {{ box-shadow: 0 0 0 8px rgba(37, 99, 235, 0); }}
    100% {{ box-shadow: 0 0 0 0 rgba(37, 99, 235, 0); }}
}}

/* 10. Animated SVG check on success token ─────────────────────────── */
.c2s-check-svg {{
    width: 28px; height: 28px;
    stroke: {SUCCESS};
    stroke-width: 3;
    stroke-linecap: round;
    fill: none;
    overflow: visible;
}}
.c2s-check-svg circle {{
    stroke-dasharray: 166;
    stroke-dashoffset: 166;
    animation: c2sStrokeIn 0.6s 0.1s cubic-bezier(0.65, 0, 0.45, 1) forwards;
}}
.c2s-check-svg path {{
    stroke-dasharray: 48;
    stroke-dashoffset: 48;
    animation: c2sStrokeIn 0.4s 0.55s cubic-bezier(0.65, 0, 0.45, 1) forwards;
}}
@keyframes c2sStrokeIn {{
    to {{ stroke-dashoffset: 0; }}
}}

/* 11. Subtle SVG noise texture overlay on the hero (premium feel) ── */
.c2s-hero::before {{
    /* Layered on top of the existing dot grid from the base block. */
    background-image:
        radial-gradient(circle, rgba(15, 23, 42, 0.05) 1px, transparent 1px),
        url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='160' height='160' viewBox='0 0 160 160'><filter id='n'><feTurbulence type='fractalNoise' baseFrequency='0.85' numOctaves='2' stitchTiles='stitch'/><feColorMatrix values='0 0 0 0 0   0 0 0 0 0   0 0 0 0 0   0 0 0 0.06 0'/></filter><rect width='100%' height='100%' filter='url(%23n)'/></svg>");
    background-size: 22px 22px, 160px 160px;
    background-blend-mode: multiply;
    opacity: 0.6;
}}

/* 12. Animated focus ring on inputs (replaces base block's static
       2px shadow with a soft expand-and-fade) ─────────────────── */
.stTextInput > div > div:focus-within,
.stNumberInput > div:focus-within,
.stSelectbox > div > div:focus-within {{
    border-color: {PRIMARY} !important;
    box-shadow:
        0 0 0 4px rgba(37, 99, 235, 0.16),
        0 0 0 1px {PRIMARY} inset;
    animation: c2sFocusBloom 0.4s ease;
}}
@keyframes c2sFocusBloom {{
    0%   {{ box-shadow: 0 0 0 0   rgba(37, 99, 235, 0.30),
                       0 0 0 1px {PRIMARY} inset; }}
    50%  {{ box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.20),
                       0 0 0 1px {PRIMARY} inset; }}
    100% {{ box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.16),
                       0 0 0 1px {PRIMARY} inset; }}
}}

/* 13. Floating action button — bottom-right "Book a service" pill
       on every customer page (hidden on /book itself via JS class) */
.c2s-fab {{
    position: fixed;
    right: 1.2rem;
    bottom: 1.2rem;
    z-index: 999;
    background: linear-gradient(135deg, {PRIMARY} 0%, {PRIMARY_DARK} 100%);
    color: #FFFFFF !important;
    text-decoration: none;
    padding: 0.85rem 1.3rem;
    border-radius: 999px;
    font-weight: 700;
    font-size: 0.92rem;
    letter-spacing: -0.005em;
    box-shadow:
        0 12px 28px -6px rgba(37, 99, 235, 0.55),
        0 6px 14px rgba(37, 99, 235, 0.25);
    display: inline-flex;
    align-items: center;
    gap: 0.5rem;
    transform: translateY(0);
    transition: transform 0.25s cubic-bezier(0.34, 1.56, 0.64, 1),
                box-shadow 0.25s ease;
    animation: c2sFabIn 0.6s 0.3s ease both;
}}
.c2s-fab:hover {{
    transform: translateY(-3px) scale(1.04);
    box-shadow:
        0 18px 36px -6px rgba(37, 99, 235, 0.55),
        0 8px 18px rgba(37, 99, 235, 0.30);
}}
.c2s-fab .arrow {{
    display: inline-block;
    transition: transform 0.25s ease;
}}
.c2s-fab:hover .arrow {{ transform: translateX(3px); }}
@keyframes c2sFabIn {{
    from {{ opacity: 0; transform: translateY(20px) scale(0.9); }}
    to   {{ opacity: 1; transform: translateY(0)    scale(1); }}
}}

/* 14. Service-card image ribbon: keep the 3px stripe but animate its
       glow on hover so the card feels charged. */
.c2s-service-card .accent-bar {{
    box-shadow: 0 0 0 0 currentColor;
    transition: box-shadow 0.3s ease;
}}
div[data-testid="stVerticalBlockBorderWrapper"]:hover .accent-bar {{
    box-shadow: 0 4px 14px -2px rgba(37, 99, 235, 0.35);
}}

/* 15. Sidebar nav links — soft slide-in highlight on hover ───────── */
a[data-testid="stPageLink-NavLink"] {{
    position: relative;
    overflow: hidden;
}}
a[data-testid="stPageLink-NavLink"]::before {{
    content: "";
    position: absolute;
    left: 0; top: 0; bottom: 0;
    width: 3px;
    background: linear-gradient(180deg, {PRIMARY} 0%, {ACCENT} 100%);
    transform: scaleY(0);
    transform-origin: top;
    transition: transform 0.3s ease;
    border-radius: 0 3px 3px 0;
}}
a[data-testid="stPageLink-NavLink"]:hover::before {{
    transform: scaleY(1);
}}

/* 16. Reduced-motion safety net ──────────────────────────────────── */
@media (prefers-reduced-motion: reduce) {{
    *, *::before, *::after {{
        animation-duration: 0.001s !important;
        animation-iteration-count: 1 !important;
        transition-duration: 0.001s !important;
        scroll-behavior: auto !important;
    }}
    .c2s-hero, .c2s-hero::before, .c2s-hero::after {{
        animation: none !important;
    }}
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
    .c2s-hero {{ padding: 1.8rem 1.1rem 1.5rem; border-radius: 18px; }}
    .c2s-hero h1.c2s-hero-title {{
        font-size: 1.85rem !important;
        letter-spacing: -0.03em;
    }}
    .c2s-hero-sub {{ font-size: 0.95rem; }}
    .c2s-stat-value {{ font-size: 1.2rem; }}
    .c2s-stat-label {{ font-size: 0.66rem; }}
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


# ── Hero block (home page) ─────────────────────────────────────────────────
def hero_block(
    *,
    eyebrow: str,
    plain_lead: str,
    accent_word: str,
    plain_tail: str = "",
    subtitle: str = "",
    stats: list[tuple[str, str]] | None = None,
) -> None:
    """Render the home-page hero with an animated gradient backdrop.

    The headline is composed as ``plain_lead <accent_word> plain_tail`` so the
    accent word can be highlighted with the brand gradient without breaking
    line-wrap. Pass up to 3 (value, label) pairs for the stat strip; passing
    ``None`` skips the strip entirely.
    """
    accent = (
        f'<span class="accent">{accent_word}</span>' if accent_word else ""
    )
    sub = (
        f'<p class="c2s-hero-sub">{subtitle}</p>' if subtitle else ""
    )

    stat_html = ""
    if stats:
        cells = "".join(
            f'<div class="c2s-stat">'
            f'  <div class="c2s-stat-value">{value}</div>'
            f'  <div class="c2s-stat-label">{label}</div>'
            f'</div>'
            for value, label in stats[:3]
        )
        stat_html = f'<div class="c2s-stat-strip">{cells}</div>'

    st.markdown(
        f'<section class="c2s-hero">'
        f'  <span class="c2s-hero-eyebrow"><span class="dot"></span>{eyebrow}</span>'
        f'  <h1 class="c2s-hero-title">{plain_lead} {accent} {plain_tail}</h1>'
        f'  {sub}'
        f'  {stat_html}'
        f'</section>',
        unsafe_allow_html=True,
    )


# ── Pills ───────────────────────────────────────────────────────────────────
# Per-category accent color used for the service-card top stripe + badge.
_CATEGORY_ACCENTS = {
    # Family → (badge bg, badge fg, accent stripe)
    "government": ("#DBEAFE", "#1D4ED8", PRIMARY),
    "vehicle":    ("#DBEAFE", "#1D4ED8", PRIMARY),
    "id":         ("#DBEAFE", "#1D4ED8", PRIMARY),
    "payment":    (SUCCESS_BG, SUCCESS_TEXT, SUCCESS),
    "bill":       (SUCCESS_BG, SUCCESS_TEXT, SUCCESS),
    "document":   (WARNING_BG, WARNING_TEXT, "#D97706"),
    "default":    (GRAY_BG,    GRAY_TEXT,    "#94A3B8"),
}


def _category_family(category: str) -> str:
    cat = (category or "").lower()
    for key in ("government", "vehicle", "id", "payment", "bill", "document"):
        if key in cat:
            return key
    return "default"


def category_accent(category: str) -> str:
    """Return the single hex color for the category accent stripe."""
    return _CATEGORY_ACCENTS[_category_family(category)][2]


def category_badge(category: str) -> str:
    """Pill colored by service-category family."""
    bg, fg, _ = _CATEGORY_ACCENTS[_category_family(category)]
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
        f'border-radius:10px; padding:0.85rem 0.6rem; text-align:center; '
        f'transition: all 0.18s ease;" '
        f'onmouseover="this.style.transform=\'translateY(-2px)\';'
        f'this.style.boxShadow=\'0 8px 20px rgba(15,23,42,0.07)\';" '
        f'onmouseout="this.style.transform=\'\';this.style.boxShadow=\'\';">'
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
        f'border-radius:14px; padding:1rem; box-shadow:0 1px 2px '
        f'rgba(15,23,42,0.04); transition: all 0.18s ease;" '
        f'onmouseover="this.style.transform=\'translateY(-2px)\';'
        f'this.style.boxShadow=\'0 8px 24px rgba(15,23,42,0.07)\';" '
        f'onmouseout="this.style.transform=\'\';'
        f'this.style.boxShadow=\'0 1px 2px rgba(15,23,42,0.04)\';">'
        f'<div style="width:38px; height:38px; border-radius:10px; '
        f'background:{tint}; color:{color}; display:inline-flex; '
        f'align-items:center; justify-content:center; font-size:1.2rem; '
        f'margin-bottom:0.55rem;">{icon}</div>'
        f'<div style="font-size:1.7rem; font-weight:800; color:{INK}; '
        f'line-height:1; letter-spacing:-0.025em;">{value}</div>'
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
    # Animated SVG check that draws itself on render — defined by
    # .c2s-check-svg / @keyframes c2sStrokeIn in the global stylesheet.
    check = (
        '<svg class="c2s-check-svg" viewBox="0 0 56 56" '
        'width="34" height="34" aria-hidden="true">'
        '<circle cx="28" cy="28" r="26"/>'
        '<path d="M16 29 L25 38 L41 19"/>'
        '</svg>'
    )
    return (
        f'<div class="c2s-reveal" '
        f'style="background:linear-gradient(180deg, {SUCCESS_BG} 0%, '
        f'#ECFDF5 100%); border:1px solid {SUCCESS}; border-radius:14px; '
        f'padding:1.4rem; box-shadow:0 4px 16px rgba(22,163,74,0.10);">'
        f'<div style="display:flex; align-items:center; gap:0.7rem; '
        f'margin-bottom:0.4rem;">{check}'
        f'<div style="font-size:0.74rem; font-weight:700; color:{SUCCESS_TEXT}; '
        f'text-transform:uppercase; letter-spacing:0.08em;">'
        f'Booking confirmed</div></div>'
        f'<div class="c2s-token" style="margin-top:0.2rem;">{token}</div>'
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
    """Standalone stat strip (3-up, used outside the hero too)."""
    cells = "".join(
        f'<div class="c2s-stat">'
        f'  <div class="c2s-stat-value">{value}</div>'
        f'  <div class="c2s-stat-label">{label}</div>'
        f'</div>'
        for value, label in stats[:3]
    )
    st.markdown(
        f'<div class="c2s-stat-strip" style="margin-bottom:1.2rem;">{cells}</div>',
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
        f'{PRIMARY_DARK} 100%); border-radius:14px; padding:1.6rem 1.2rem; '
        f'color:#FFFFFF; margin:1.6rem 0; box-shadow:0 8px 24px '
        f'rgba(37,99,235,0.18);">'
        f'<div style="font-size:0.74rem; font-weight:700; text-transform:'
        f'uppercase; letter-spacing:0.08em; opacity:0.85;">{eyebrow}</div>'
        f'<h2 style="color:#FFFFFF !important; font-size:1.4rem !important; '
        f'font-weight:700 !important; margin:0.4rem 0 0.4rem !important;">'
        f'{title_html}</h2>'
        f'<div style="opacity:0.9; font-size:0.95rem;">{subtitle}</div>'
        f'</div>',
        unsafe_allow_html=True,
    )



# ──────────────────────────────────────────────────────────────────────────
# 3D + dynamic helpers (added in style/3d-dynamic-upgrade)
# ──────────────────────────────────────────────────────────────────────────
# These ride on top of the CSS layer above. They're optional from the page's
# point of view — pages that don't call them just get the CSS effects (mesh
# gradient, hero sheen, card 3D tilt, button shimmer, sidebar slide-in
# highlight). The helpers below add the bits that need an HTML payload
# (animated SVG check, scroll-reveal observer, floating "Book" pill).

# Tiny IntersectionObserver script that adds .c2s-revealed when an element
# scrolls into view. Idempotent — guarded by session_state so we only inject
# the script tag once per Streamlit run.
_SCROLL_REVEAL_JS = """
<script>
(function () {
  if (window.__c2sRevealReady) return;
  window.__c2sRevealReady = true;
  function init() {
    var els = document.querySelectorAll('.c2s-reveal, h2');
    if (!('IntersectionObserver' in window)) {
      // Fallback: just reveal everything immediately.
      els.forEach(function (el) { el.classList.add('c2s-revealed'); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (e) {
        if (e.isIntersecting) {
          e.target.classList.add('c2s-revealed');
          io.unobserve(e.target);
        }
      });
    }, { rootMargin: '0px 0px -8% 0px', threshold: 0.05 });
    els.forEach(function (el) { io.observe(el); });
  }
  // Streamlit re-renders the DOM frequently; rerun the observer attach on
  // each animation frame for a short window to catch newly-mounted nodes.
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }
  // Re-attach on Streamlit's mutation pulses for the first 8 seconds.
  var startedAt = Date.now();
  var observer = new MutationObserver(function () {
    if (Date.now() - startedAt > 8000) { observer.disconnect(); return; }
    init();
  });
  observer.observe(document.body, { childList: true, subtree: true });
})();
</script>
"""


def inject_scroll_reveal() -> None:
    """Drop the IntersectionObserver script once per page.

    Call this from any page that wants ``.c2s-reveal`` elements (and H2s,
    which are auto-targeted) to fade up as they scroll into view.
    """
    if st.session_state.get("_c2s_scroll_reveal_injected"):
        return
    st.markdown(_SCROLL_REVEAL_JS, unsafe_allow_html=True)
    st.session_state["_c2s_scroll_reveal_injected"] = True


def animated_check_svg(*, size: int = 28) -> str:
    """Inline SVG of a stroked check mark inside a circle.

    The SVG draws itself with a stroke-dashoffset animation defined in the
    global stylesheet (``.c2s-check-svg``). Use it on the success token
    card or anywhere a "completed" feel matters.
    """
    return (
        f'<svg class="c2s-check-svg" viewBox="0 0 56 56" '
        f'width="{size}" height="{size}" aria-hidden="true">'
        f'<circle cx="28" cy="28" r="26"/>'
        f'<path d="M16 29 L25 38 L41 19"/>'
        f'</svg>'
    )


def floating_book_button(
    *, label: str = "Book a service", target: str = "/book",
) -> None:
    """Render a fixed-position pill at bottom-right that links to /book.

    Hidden via the ``data-c2s-fab-hide`` attribute on the html tag if a
    page wants to suppress it (e.g. the booking page itself shouldn't
    show a 'Go to booking' shortcut).
    """
    # Skip when explicitly suppressed for this page.
    if st.session_state.get("_c2s_fab_suppress"):
        return
    if st.session_state.get("_c2s_fab_rendered"):
        return
    arrow = '<span class="arrow">→</span>'
    st.markdown(
        f'<a class="c2s-fab" href="{target}" target="_self">'
        f'<span>📝</span><span>{label}</span>{arrow}'
        f'</a>',
        unsafe_allow_html=True,
    )
    st.session_state["_c2s_fab_rendered"] = True


def suppress_floating_book_button() -> None:
    """Call from /book or owner pages so the FAB stays hidden."""
    st.session_state["_c2s_fab_suppress"] = True
