"""AI document checker — runs on every upload before submission.

Purpose
-------
Most rejected govt-paperwork applications fail because the supporting
photo was blurry, badly lit, or cropped. This module catches those
issues *at upload time* so the customer can retake the photo before
the booking goes in. Reduces rework for the shop and frustration for
the customer.

What it checks (no external API, no network calls, no API keys)
---------------------------------------------------------------
1. **File format**       — must be JPEG / PNG / WebP for image checks,
                            PDF accepted as-is (basic size validation).
2. **File size**         — at least 50 KB, at most 10 MB.
3. **Resolution**        — minimum 800 × 600 px for ID-style documents.
4. **Sharpness / blur**  — Laplacian-style edge variance via PIL filters
                            and numpy. Below threshold → "blurry, retake".
5. **Lighting**          — luminance histogram mean.
                            <60  → too dark.
                            >220 → overexposed.
6. **Aspect ratio**      — for ID-card categories, the photo's aspect
                            ratio is compared against a known target
                            (Aadhaar ≈ 1.586:1) so heavily-cropped photos
                            are flagged.

The result is a ``DocumentReport`` with:
- ``score``       — 0–100 overall quality grade
- ``is_valid``    — True iff there are zero blocker checks
- ``checks``      — list of individual ``DocumentCheck`` rows
- ``hint``        — single human sentence summarising what to fix

The page UI renders this directly via :func:`render_report_html`.

Future v2 (not in this release)
-------------------------------
- Plug pytesseract for OCR-based content detection (Aadhaar number
  pattern, government keywords).
- Optional GPT-4V / Gemini Vision call for shops willing to pay
  ~₹0.85 per check, for tampering detection and photo–document
  match.

Both can drop in without changing this module's public API.
"""
from __future__ import annotations

import io
import logging
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)

# ── Tunable thresholds ──────────────────────────────────────────────────────
MIN_BYTES = 50 * 1024              # 50 KB
MAX_BYTES = 10 * 1024 * 1024       # 10 MB
MIN_WIDTH = 800
MIN_HEIGHT = 600
BLUR_VARIANCE_FLOOR = 80.0          # below this → blurry
BRIGHTNESS_MIN = 60.0
BRIGHTNESS_MAX = 220.0
ID_CARD_TARGET_RATIO = 1.586        # Aadhaar / PAN / driving licence
ID_CARD_RATIO_TOLERANCE = 0.40      # allow generous slack

ALLOWED_IMAGE_FORMATS = {"JPEG", "PNG", "WEBP"}
ALLOWED_PDF_EXTENSIONS = {".pdf"}


# ── Severity tiers ──────────────────────────────────────────────────────────
SEVERITY_BLOCKER = "blocker"  # must fix before submission
SEVERITY_WARNING = "warning"  # may fix; lowers score but allowed through
SEVERITY_INFO = "info"        # informational only, no impact on score


@dataclass
class DocumentCheck:
    """A single check row (pass/fail + human reason)."""
    label: str
    passed: bool
    severity: str
    detail: str

    @property
    def icon(self) -> str:
        if self.passed:
            return "\u2713"  # ✓
        if self.severity == SEVERITY_BLOCKER:
            return "\u2717"  # ✗
        return "\u26A0"      # ⚠

    @property
    def color(self) -> str:
        if self.passed:
            return "#16A34A"  # success green
        if self.severity == SEVERITY_BLOCKER:
            return "#DC2626"  # danger red
        return "#D97706"      # warning amber


@dataclass
class DocumentReport:
    """Aggregate result returned to the page."""
    is_valid: bool                  # True iff zero blockers
    score: int                      # 0..100
    checks: list[DocumentCheck] = field(default_factory=list)
    hint: str = ""                  # one-sentence summary
    is_pdf: bool = False            # we couldn't run image-quality checks
    bypassed: bool = False          # set when checks couldn't run at all


# ──────────────────────────────────────────────────────────────────────────
# Public entry point
# ──────────────────────────────────────────────────────────────────────────
def check_document(
    *,
    file_bytes: bytes,
    file_name: str = "",
    expected_aspect_ratio: Optional[float] = None,
) -> DocumentReport:
    """Run every available check and return a single report.

    ``expected_aspect_ratio`` is used to compare ID-card-shaped uploads
    against a known target (e.g. ``1.586`` for Aadhaar). Pass ``None``
    to skip the aspect-ratio check.
    """
    report = DocumentReport(is_valid=True, score=100, checks=[])

    # PDFs get a couple of basic checks but skip image-quality analysis.
    if file_name.lower().endswith(tuple(ALLOWED_PDF_EXTENSIONS)):
        report.is_pdf = True
        _check_size(report, file_bytes)
        report.checks.append(DocumentCheck(
            label="File type",
            passed=True,
            severity=SEVERITY_INFO,
            detail="PDF \u2014 image-quality checks skipped",
        ))
        report.hint = (
            "PDF uploads are accepted as-is. For best results upload a "
            "high-resolution photo (JPEG/PNG)."
        )
        return _finalize(report)

    # All other paths require Pillow. If something goes wrong we surface
    # a single blocker and let the page handle it gracefully.
    try:
        from PIL import Image, ImageFilter  # transitive Streamlit dep
        import numpy as np                  # transitive pandas dep
    except Exception as exc:                # noqa: BLE001
        logger.warning("Pillow / numpy unavailable for doc check: %s", exc)
        report.bypassed = True
        report.hint = "Document quality checks could not run on this server."
        return report

    _check_size(report, file_bytes)
    if not _is_valid(report.checks):
        return _finalize(report)

    # Open the image once, hand the loaded object to each sub-check.
    try:
        image = Image.open(io.BytesIO(file_bytes))
        image.load()  # force decode now so corrupt files fail here
    except Exception as exc:  # noqa: BLE001
        report.checks.append(DocumentCheck(
            label="Image valid",
            passed=False,
            severity=SEVERITY_BLOCKER,
            detail=f"Could not read image: {exc}",
        ))
        return _finalize(report)

    _check_format(report, image)
    if not _is_valid(report.checks):
        return _finalize(report)

    _check_resolution(report, image)
    _check_blur(report, image, np, ImageFilter)
    _check_brightness(report, image, np)
    if expected_aspect_ratio:
        _check_aspect_ratio(report, image, expected_aspect_ratio)

    return _finalize(report)


# ──────────────────────────────────────────────────────────────────────────
# Individual checks
# ──────────────────────────────────────────────────────────────────────────
def _check_size(report: DocumentReport, file_bytes: bytes) -> None:
    size = len(file_bytes)
    size_kb = size / 1024
    if size < MIN_BYTES:
        report.checks.append(DocumentCheck(
            label="File size",
            passed=False,
            severity=SEVERITY_WARNING,
            detail=f"Only {size_kb:.0f} KB \u2014 image may be too low quality",
        ))
    elif size > MAX_BYTES:
        report.checks.append(DocumentCheck(
            label="File size",
            passed=False,
            severity=SEVERITY_BLOCKER,
            detail=f"{size_kb / 1024:.1f} MB exceeds the 10 MB limit",
        ))
    else:
        if size > 1024 * 1024:
            human = f"{size / 1024 / 1024:.1f} MB"
        else:
            human = f"{size_kb:.0f} KB"
        report.checks.append(DocumentCheck(
            label="File size",
            passed=True,
            severity=SEVERITY_INFO,
            detail=human,
        ))


def _check_format(report: DocumentReport, image) -> None:
    fmt = (image.format or "").upper()
    if fmt in ALLOWED_IMAGE_FORMATS:
        report.checks.append(DocumentCheck(
            label="File format",
            passed=True,
            severity=SEVERITY_INFO,
            detail=fmt,
        ))
    else:
        report.checks.append(DocumentCheck(
            label="File format",
            passed=False,
            severity=SEVERITY_BLOCKER,
            detail=(
                f"Format {fmt or 'unknown'} not supported \u2014 please upload "
                f"JPEG, PNG, or WebP"
            ),
        ))


def _check_resolution(report: DocumentReport, image) -> None:
    w, h = image.size
    if w < MIN_WIDTH or h < MIN_HEIGHT:
        report.checks.append(DocumentCheck(
            label="Resolution",
            passed=False,
            severity=SEVERITY_WARNING,
            detail=(
                f"{w}\u00d7{h} \u2014 recommend at least {MIN_WIDTH}\u00d7"
                f"{MIN_HEIGHT} for legible scans"
            ),
        ))
    else:
        report.checks.append(DocumentCheck(
            label="Resolution",
            passed=True,
            severity=SEVERITY_INFO,
            detail=f"{w}\u00d7{h}",
        ))


def _check_blur(report: DocumentReport, image, np, ImageFilter) -> None:
    """Approximate Laplacian variance via PIL's edge filter + numpy var."""
    try:
        gray = image.convert("L")
        # Downsample large images so the variance is comparable across sizes.
        max_side = 1024
        if max(gray.size) > max_side:
            scale = max_side / max(gray.size)
            new_size = (int(gray.size[0] * scale), int(gray.size[1] * scale))
            gray = gray.resize(new_size)
        edges = gray.filter(ImageFilter.FIND_EDGES)
        arr = np.array(edges, dtype=np.float32)
        variance = float(arr.var())
    except Exception as exc:  # noqa: BLE001
        logger.warning("blur check failed: %s", exc)
        return  # silently skip rather than fail the upload

    if variance < BLUR_VARIANCE_FLOOR:
        report.checks.append(DocumentCheck(
            label="Sharpness",
            passed=False,
            severity=SEVERITY_WARNING,
            detail=(
                f"Photo looks soft (sharpness score {variance:.0f}). "
                f"Hold the camera steady and refocus."
            ),
        ))
    else:
        # Translate variance into a friendly 0–100 score so customers
        # see "Sharpness 87/100" rather than a raw number.
        score = min(100, int(round(variance / 10)))
        report.checks.append(DocumentCheck(
            label="Sharpness",
            passed=True,
            severity=SEVERITY_INFO,
            detail=f"Sharp ({score}/100)",
        ))


def _check_brightness(report: DocumentReport, image, np) -> None:
    try:
        gray = image.convert("L")
        arr = np.array(gray, dtype=np.float32)
        mean = float(arr.mean())
    except Exception as exc:  # noqa: BLE001
        logger.warning("brightness check failed: %s", exc)
        return

    if mean < BRIGHTNESS_MIN:
        report.checks.append(DocumentCheck(
            label="Lighting",
            passed=False,
            severity=SEVERITY_WARNING,
            detail=(
                f"Image is too dark (avg brightness {mean:.0f}/255). "
                f"Try better lighting or move outdoors."
            ),
        ))
    elif mean > BRIGHTNESS_MAX:
        report.checks.append(DocumentCheck(
            label="Lighting",
            passed=False,
            severity=SEVERITY_WARNING,
            detail=(
                f"Image is overexposed (avg brightness {mean:.0f}/255). "
                f"Avoid direct flash or shiny lamination."
            ),
        ))
    else:
        report.checks.append(DocumentCheck(
            label="Lighting",
            passed=True,
            severity=SEVERITY_INFO,
            detail=f"Good ({mean:.0f}/255)",
        ))


def _check_aspect_ratio(report: DocumentReport, image,
                        expected: float) -> None:
    w, h = image.size
    actual = max(w, h) / max(min(w, h), 1)
    delta = abs(actual - expected)
    if delta <= ID_CARD_RATIO_TOLERANCE:
        report.checks.append(DocumentCheck(
            label="Card framing",
            passed=True,
            severity=SEVERITY_INFO,
            detail=f"Aspect ratio looks like an ID card ({actual:.2f}:1)",
        ))
    else:
        report.checks.append(DocumentCheck(
            label="Card framing",
            passed=False,
            severity=SEVERITY_WARNING,
            detail=(
                f"Aspect ratio {actual:.2f}:1 doesn't look like an ID card "
                f"(expected ~{expected:.2f}:1). Capture the whole card "
                f"with a small margin."
            ),
        ))


# ──────────────────────────────────────────────────────────────────────────
# Aggregation
# ──────────────────────────────────────────────────────────────────────────
def _is_valid(checks: list[DocumentCheck]) -> bool:
    return not any(
        not c.passed and c.severity == SEVERITY_BLOCKER for c in checks
    )


def _compute_score(checks: list[DocumentCheck]) -> int:
    """Score = 100 minus penalties for failed warnings/blockers."""
    score = 100
    for c in checks:
        if c.passed:
            continue
        if c.severity == SEVERITY_BLOCKER:
            score -= 40
        elif c.severity == SEVERITY_WARNING:
            score -= 12
    return max(0, min(100, score))


def _build_hint(report: DocumentReport) -> str:
    """One short sentence the page can headline above the checks."""
    failed = [c for c in report.checks if not c.passed]
    if not failed:
        return "Looks great \u2014 clear, well-lit, and the right size."
    blockers = [c for c in failed if c.severity == SEVERITY_BLOCKER]
    if blockers:
        return (
            "We can't accept this file as-is \u2014 see the red rows below."
        )
    # No blockers, just warnings — first warning becomes the headline.
    first = failed[0]
    return f"Looks usable, but you can do better: {first.label.lower()}."


def _finalize(report: DocumentReport) -> DocumentReport:
    report.is_valid = _is_valid(report.checks)
    report.score = _compute_score(report.checks)
    report.hint = _build_hint(report)
    return report


# ──────────────────────────────────────────────────────────────────────────
# Convenience: render a report into HTML for st.markdown(unsafe_allow_html)
# ──────────────────────────────────────────────────────────────────────────
def render_report_html(report: DocumentReport, *, file_label: str) -> str:
    """Render a single-file report as a card the booking page can display."""
    if report.bypassed:
        return (
            f'<div style="background:#FFF7ED; border:1px solid #FDBA74; '
            f'border-radius:12px; padding:0.9rem 1rem; margin-bottom:0.6rem;">'
            f'<div style="font-weight:600; color:#92400E;">'
            f'AI checks unavailable on this server</div>'
            f'<div style="color:#78350F; font-size:0.86rem; margin-top:0.2rem;">'
            f'{file_label} will be uploaded without verification.</div>'
            f'</div>'
        )

    score = report.score
    if score >= 85:
        bar_color, badge_bg, badge_fg, badge_text = (
            "#16A34A", "#DCFCE7", "#15803D", "AI-verified"
        )
    elif score >= 60:
        bar_color, badge_bg, badge_fg, badge_text = (
            "#D97706", "#FEF3C7", "#92400E", "Acceptable"
        )
    else:
        bar_color, badge_bg, badge_fg, badge_text = (
            "#DC2626", "#FEE2E2", "#B91C1C", "Needs retake"
        )

    rows = "".join(
        f'<div style="display:flex; gap:0.6rem; padding:0.32rem 0; '
        f'border-top:1px solid #F1F5F9;">'
        f'<div style="color:{c.color}; font-weight:700; width:1rem; '
        f'flex-shrink:0;">{c.icon}</div>'
        f'<div style="flex:1;">'
        f'<div style="font-size:0.88rem; font-weight:600; color:#0F172A;">'
        f'{c.label}</div>'
        f'<div style="font-size:0.82rem; color:#64748B;">{c.detail}</div>'
        f'</div></div>'
        for c in report.checks
    )

    return (
        f'<div style="background:#FFFFFF; border:1px solid #E2E8F0; '
        f'border-radius:14px; padding:1rem 1.1rem; margin-bottom:0.6rem; '
        f'box-shadow:0 1px 2px rgba(15,23,42,0.04);">'
        # Top row: file name + score badge
        f'<div style="display:flex; align-items:center; '
        f'justify-content:space-between; gap:0.6rem; margin-bottom:0.4rem;">'
        f'<div style="font-weight:600; color:#0F172A; font-size:0.92rem; '
        f'overflow:hidden; text-overflow:ellipsis; white-space:nowrap;">'
        f'\U0001F4CE {file_label}</div>'
        f'<span style="background:{badge_bg}; color:{badge_fg}; '
        f'padding:0.18rem 0.6rem; border-radius:999px; font-size:0.74rem; '
        f'font-weight:700; flex-shrink:0;">{badge_text} \u00b7 {score}/100</span>'
        f'</div>'
        # Score bar
        f'<div style="width:100%; height:6px; background:#F1F5F9; '
        f'border-radius:3px; overflow:hidden; margin:0.3rem 0 0.6rem;">'
        f'<div style="width:{score}%; height:100%; background:{bar_color}; '
        f'transition:width 0.5s ease;"></div>'
        f'</div>'
        # Hint
        f'<div style="color:#374151; font-size:0.86rem; line-height:1.45; '
        f'margin-bottom:0.4rem;">{report.hint}</div>'
        # Detailed rows
        f'<div style="margin-top:0.4rem;">{rows}</div>'
        f'</div>'
    )


def aspect_ratio_for_category(category: str) -> Optional[float]:
    """Look up the expected aspect ratio for a service category.

    Returns ``None`` for non-ID-card services (where aspect-ratio
    checking would just create false negatives).
    """
    cat = (category or "").lower()
    # All Indian govt ID cards (Aadhaar, PAN, voter ID, driving licence)
    # are credit-card sized: 85.6 × 53.98 mm → 1.586:1
    id_keywords = (
        "id", "aadhaar", "pan", "voter", "licence", "license",
        "vehicle", "driving",
    )
    if any(k in cat for k in id_keywords):
        return ID_CARD_TARGET_RATIO
    return None
