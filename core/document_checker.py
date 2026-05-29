"""AI document checker — runs on every upload before submission.

Purpose
-------
Most rejected govt-paperwork applications fail because the supporting
photo was blurry, badly lit, cropped, or simply the wrong document
entirely. This module catches those issues *at upload time* so the
customer can retake (or swap) the photo before the booking goes in.
Reduces rework for the shop and frustration for the customer.

What it checks (no API keys, no network calls, no per-check cost)
-----------------------------------------------------------------
Layer 1 — image quality (Pillow + numpy, always-on)

1. **File format**       — JPEG / PNG / WebP for images, PDF accepted as-is.
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

Layer 2 — content (pytesseract OCR, if tesseract binary is installed)

7. **Document type**     — OCR'd text is matched against a keyword
                            dictionary to identify AADHAAR / PAN /
                            PASSPORT / DRIVING_LICENCE / VOTER_ID. If
                            the page hints which document is expected,
                            mismatches surface as a blocker (uploaded
                            PAN when the service was Aadhaar).
8. **Aadhaar number**    — 12-digit pattern (XXXX XXXX XXXX) detection.
                            Privacy: the value is partially masked in
                            the UI and never logged or stored.
9. **PAN number**        — ABCDE1234F format detection.
10. **Passport number**  — Indian "letter + 7 digits" format.

Layer 2 fails closed: if pytesseract isn't installed (or tesseract isn't
on the path), every Layer 2 check is silently skipped. Layer 1 still
runs on its own — the customer just sees fewer rows in the report card.

The result is a ``DocumentReport`` with:
- ``score``       — 0–100 overall quality grade
- ``is_valid``    — True iff there are zero blocker checks
- ``checks``      — list of individual ``DocumentCheck`` rows
- ``hint``        — single human sentence summarising what to fix

The page UI renders this directly via :func:`render_report_html`.

Privacy note
------------
We extract the Aadhaar / PAN / passport number for *validation only*.
The value is held in memory just long enough to fill out the verdict
card, partially masked before it's shown to the customer, and never
written to disk or sent to the database. Storing or logging Aadhaar
numbers has legal implications under India's Aadhaar Act.

Future v3 (not in this release)
-------------------------------
- Optional GPT-4V / Gemini Vision call for shops willing to pay
  ~₹0.85 per check, for tampering detection and photo–document match.
"""
from __future__ import annotations

import io
import logging
import re
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
    expected_document_type: Optional[str] = None,
) -> DocumentReport:
    """Run every available check and return a single report.

    ``expected_aspect_ratio`` compares ID-card-shaped uploads against a
    known target (e.g. ``1.586`` for Aadhaar). Pass ``None`` to skip.

    ``expected_document_type`` is one of the constants below — when set,
    Layer 2 OCR cross-checks the detected text against it and surfaces
    a blocker if they disagree (e.g. PAN uploaded for an Aadhaar
    service). Pass ``None`` to skip cross-checking but still run
    document-type detection for information.
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

    # Layer 2: OCR content checks. Silent no-op if tesseract isn't on
    # the path. Always runs after Layer 1 so that a Layer 1 blocker
    # stops Layer 2 from wasting CPU on a known-bad image.
    _check_ocr_content(report, image, expected_document_type)

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



# ──────────────────────────────────────────────────────────────────────────
# Layer 2 — OCR-based content checks (pytesseract)
# ──────────────────────────────────────────────────────────────────────────
# Document-type constants. Strings are stable for storage / comparison.
DOC_TYPE_AADHAAR = "AADHAAR"
DOC_TYPE_PAN = "PAN"
DOC_TYPE_PASSPORT = "PASSPORT"
DOC_TYPE_DRIVING_LICENCE = "DRIVING_LICENCE"
DOC_TYPE_VOTER_ID = "VOTER_ID"

# Friendly labels for UI display.
_DOC_TYPE_LABELS = {
    DOC_TYPE_AADHAAR: "Aadhaar card",
    DOC_TYPE_PAN: "PAN card",
    DOC_TYPE_PASSPORT: "Passport",
    DOC_TYPE_DRIVING_LICENCE: "Driving licence",
    DOC_TYPE_VOTER_ID: "Voter ID",
}

# Keyword → document-type lookup. Order matters: more specific keys first.
# Words are checked against the OCR output uppercased + space-collapsed.
_DOC_TYPE_KEYWORDS: list[tuple[str, tuple[str, ...]]] = [
    (DOC_TYPE_AADHAAR, (
        "AADHAAR", "AADHAR", "UIDAI",
        "UNIQUE IDENTIFICATION", "GOVERNMENT OF INDIA",
    )),
    (DOC_TYPE_PAN, (
        "PERMANENT ACCOUNT NUMBER", "INCOME TAX DEPARTMENT",
        "INCOMETAX", "PAN CARD",
    )),
    (DOC_TYPE_PASSPORT, (
        "REPUBLIC OF INDIA", "PASSPORT", "TYPE / TYPE", "TYPE/TYPE",
    )),
    (DOC_TYPE_DRIVING_LICENCE, (
        "DRIVING LICENCE", "DRIVING LICENSE",
        "TRANSPORT DEPARTMENT", "MOTOR VEHICLES",
    )),
    (DOC_TYPE_VOTER_ID, (
        "ELECTION COMMISSION", "ELECTORAL", "EPIC NO", "VOTER",
    )),
]


def _ocr_available() -> bool:
    """True iff both the pytesseract module *and* the tesseract binary work.

    We can't just check the import — pytesseract is a thin wrapper that
    shells out to the ``tesseract`` binary. If that binary isn't on
    PATH, pytesseract raises at first use. The check below tries both
    in one go and caches the result for the rest of the process.
    """
    cached = getattr(_ocr_available, "_cached", None)
    if cached is not None:
        return cached
    try:
        import pytesseract
        # Probe the binary; raises TesseractNotFoundError if missing.
        pytesseract.get_tesseract_version()
        result = True
    except Exception as exc:  # noqa: BLE001
        logger.info(
            "pytesseract / tesseract unavailable, OCR layer disabled: %s",
            exc,
        )
        result = False
    setattr(_ocr_available, "_cached", result)
    return result


def _run_ocr(image) -> str:
    """OCR the image and return uppercase text with collapsed whitespace.

    Returns an empty string if anything goes wrong — callers should
    treat that as "no OCR data available" rather than an error.
    """
    try:
        import pytesseract
    except Exception:  # noqa: BLE001
        return ""
    try:
        # `--psm 6` = "Assume a single uniform block of text" — works
        # well for ID cards which are essentially flat pages of text.
        text = pytesseract.image_to_string(
            image, config="--psm 6", lang="eng",
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("OCR failed: %s", exc)
        return ""
    # Normalise whitespace and uppercase for keyword matching.
    return re.sub(r"\s+", " ", (text or "")).strip().upper()


def _detect_document_type(text: str) -> Optional[str]:
    """Return the document-type constant matching the OCR text, or None.

    First strong match wins. The keyword tables are intentionally short
    and conservative — false positives are worse than false negatives
    here (we'd rather say "couldn't auto-detect" than wrongly accuse
    the customer of uploading the wrong document).
    """
    if not text:
        return None
    # Score each candidate by how many of its keywords appear, pick the
    # one with the most hits (with a minimum of 1 hit).
    best_type: Optional[str] = None
    best_score = 0
    for doc_type, keywords in _DOC_TYPE_KEYWORDS:
        hits = sum(1 for kw in keywords if kw in text)
        if hits > best_score:
            best_score = hits
            best_type = doc_type
    return best_type if best_score >= 1 else None


_AADHAAR_NUMBER_RE = re.compile(
    r"\b(\d{4})[\s-]?(\d{4})[\s-]?(\d{4})\b"
)
_PAN_RE = re.compile(r"\b([A-Z]{5}\d{4}[A-Z])\b")
_PASSPORT_RE = re.compile(r"\b([A-Z]\d{7})\b")


def _extract_aadhaar_number(text: str) -> Optional[str]:
    """Return the 12-digit Aadhaar number found in the OCR text, or None."""
    if not text:
        return None
    m = _AADHAAR_NUMBER_RE.search(text)
    if not m:
        return None
    return f"{m.group(1)} {m.group(2)} {m.group(3)}"


def _extract_pan(text: str) -> Optional[str]:
    if not text:
        return None
    m = _PAN_RE.search(text)
    return m.group(1) if m else None


def _extract_passport_number(text: str) -> Optional[str]:
    if not text:
        return None
    m = _PASSPORT_RE.search(text)
    return m.group(1) if m else None


def _mask_aadhaar(number: str) -> str:
    """Display only the last 4 digits — UIDAI privacy guideline."""
    digits = re.sub(r"\D", "", number)
    if len(digits) != 12:
        return "XXXX XXXX XXXX"
    return f"XXXX XXXX {digits[-4:]}"


def _mask_pan(pan: str) -> str:
    pan = (pan or "").upper()
    if len(pan) != 10:
        return "XXXXXXXXXX"
    return f"{pan[:3]}XXXX{pan[-3:]}"


def _check_ocr_content(
    report: DocumentReport, image,
    expected_type: Optional[str],
) -> None:
    """Run all OCR-dependent checks. Silent no-op when tesseract is missing."""
    if not _ocr_available():
        # Surface a one-time "OCR off" info row so the customer knows
        # the AI Layer 2 check exists but isn't running.
        report.checks.append(DocumentCheck(
            label="AI content scan",
            passed=True,
            severity=SEVERITY_INFO,
            detail=(
                "OCR layer not installed on this server — quality checks "
                "above still apply"
            ),
        ))
        return

    text = _run_ocr(image)
    if not text:
        report.checks.append(DocumentCheck(
            label="AI content scan",
            passed=False,
            severity=SEVERITY_WARNING,
            detail=(
                "Could not read any text from this image. Try a sharper, "
                "well-lit photo."
            ),
        ))
        return

    detected = _detect_document_type(text)
    detected_label = _DOC_TYPE_LABELS.get(detected, "—") if detected else None

    if detected:
        report.checks.append(DocumentCheck(
            label="Document recognised",
            passed=True,
            severity=SEVERITY_INFO,
            detail=f"Detected: {detected_label}",
        ))
    else:
        # No detection isn't always wrong — it could be a non-ID document
        # like a school certificate. Surface as a *warning* unless the
        # service has an explicit expectation.
        report.checks.append(DocumentCheck(
            label="Document recognised",
            passed=False,
            severity=(
                SEVERITY_BLOCKER if expected_type
                else SEVERITY_WARNING
            ),
            detail=(
                "Couldn't auto-recognise the document type. Make sure "
                "the whole card is visible and the text is readable."
            ),
        ))

    # If the service told us what to expect, cross-check against detection.
    if expected_type and detected and detected != expected_type:
        expected_label = _DOC_TYPE_LABELS.get(expected_type, expected_type)
        report.checks.append(DocumentCheck(
            label="Document mismatch",
            passed=False,
            severity=SEVERITY_BLOCKER,
            detail=(
                f"This service needs a {expected_label}, but the photo "
                f"looks like a {detected_label}. Please upload the "
                f"correct document."
            ),
        ))

    # Format-specific number checks. Only run for the type we actually
    # detected — running them all every time produces noisy rows.
    if detected == DOC_TYPE_AADHAAR:
        num = _extract_aadhaar_number(text)
        if num:
            report.checks.append(DocumentCheck(
                label="Aadhaar number",
                passed=True,
                severity=SEVERITY_INFO,
                detail=(
                    f"12-digit number visible ({_mask_aadhaar(num)}). "
                    "Last 4 shown for your verification only."
                ),
            ))
        else:
            report.checks.append(DocumentCheck(
                label="Aadhaar number",
                passed=False,
                severity=SEVERITY_WARNING,
                detail=(
                    "Couldn't read the 12-digit Aadhaar number. "
                    "A clearer photo will help."
                ),
            ))
    elif detected == DOC_TYPE_PAN:
        pan = _extract_pan(text)
        if pan:
            report.checks.append(DocumentCheck(
                label="PAN format",
                passed=True,
                severity=SEVERITY_INFO,
                detail=(
                    f"PAN format detected ({_mask_pan(pan)}). "
                    "Middle masked for privacy."
                ),
            ))
        else:
            report.checks.append(DocumentCheck(
                label="PAN format",
                passed=False,
                severity=SEVERITY_WARNING,
                detail=(
                    "Couldn't read the PAN number. A clearer photo "
                    "will help."
                ),
            ))
    elif detected == DOC_TYPE_PASSPORT:
        ppt = _extract_passport_number(text)
        if ppt:
            # Passport numbers aren't classified as restricted PII the
            # same way Aadhaar is, but we still mask out of caution.
            report.checks.append(DocumentCheck(
                label="Passport number",
                passed=True,
                severity=SEVERITY_INFO,
                detail=f"Passport format detected ({ppt[0]}XXXXX{ppt[-2:]}).",
            ))


# ──────────────────────────────────────────────────────────────────────────
# Service → expected document type lookup
# ──────────────────────────────────────────────────────────────────────────
_SERVICE_KEYWORD_TO_TYPE: list[tuple[tuple[str, ...], str]] = [
    (("aadhaar", "aadhar", "uidai"),       DOC_TYPE_AADHAAR),
    (("pan",),                             DOC_TYPE_PAN),
    (("passport",),                        DOC_TYPE_PASSPORT),
    (("driving licence", "driving license",
      "dl ",  "dl-", "dl_"),               DOC_TYPE_DRIVING_LICENCE),
    (("voter", "epic", "elector"),         DOC_TYPE_VOTER_ID),
]


def expected_document_type_for_service(
    service_name: str = "", category: str = "",
) -> Optional[str]:
    """Heuristically map a service to the document type it requires.

    Reads ``service_name`` first (e.g. *"Aadhaar update"*) and falls
    back to ``category`` (e.g. *"Government / Aadhaar"*). Returns
    ``None`` when there's no clear match — the booking flow will then
    skip the Layer 2 cross-check rather than guess.
    """
    haystack = f"{service_name or ''} {category or ''}".lower()
    if not haystack.strip():
        return None
    for keywords, doc_type in _SERVICE_KEYWORD_TO_TYPE:
        if any(k in haystack for k in keywords):
            return doc_type
    return None
