"""Customer booking form — pick service, fill details, upload docs, get token.

Three logical steps shown as a progress bar:
    1. Details      (service + personal info)
    2. Upload       (supporting documents)
    3. Confirm      (submit + receive token)

In Streamlit's single-page model these are all on one page; the bar is a
visual cue. Step 1+2 are highlighted before submit, step 3 after.

Document uploads run through ``core.document_checker`` immediately on
selection so the customer sees a quality verdict (sharpness, lighting,
framing, score 0-100) BEFORE submitting. Photos that fail blocker checks
are not allowed through; warning-level issues lower the score but still
let the customer submit.
"""
from __future__ import annotations

import re

import streamlit as st

from core.db import create_booking, get_shop_config, list_services, save_document
from core.document_checker import (
    aspect_ratio_for_category, check_document,
    expected_document_type_for_service, render_report_html,
)
from core.email_sender import send_booking_email
from core.notifications import (
    customer_booking_confirmation_chat_url,
    notify_customer_booking_confirmation_sms,
    notify_customer_booking_confirmation_twilio,
)
from core.styles import (
    BORDER, INK, MUTED, PRIMARY, category_badge, inject_global_css,
    progress_steps, section_header, subhead, success_token_card,
)

inject_global_css()

PHONE_RE = re.compile(r"^[6-9]\d{9}$")  # Indian mobile, 10 digits, 6-9 prefix


section_header(
    eyebrow="Book a service",
    title="Tell us what you need.",
    subtitle="Fill in your details — you'll receive a token number to "
             "track your booking.",
)


# ── Progress bar — highlight step 1 until submission ────────────────────────
current_step = st.session_state.get("c2s_book_step", 1)
st.markdown(
    progress_steps(["Details", "Upload", "Confirm"], current=current_step),
    unsafe_allow_html=True,
)


# ── Service Details ─────────────────────────────────────────────────────────
services = list_services(active_only=True)
if not services:
    st.error("No services are currently available. Please check back later.")
    st.stop()

# Pre-select via ?service=ID query param or session state
default_idx = 0
qp_service = st.query_params.get("service")
if qp_service:
    try:
        st.session_state["selected_service_id"] = int(qp_service)
    except (TypeError, ValueError):
        pass
preselected = st.session_state.get("selected_service_id")
if preselected:
    for i, s in enumerate(services):
        if s["id"] == preselected:
            default_idx = i
            break

subhead("Service Details")

service_labels = [
    f"{s['name']} — ₹{(s['govt_fee'] or 0) + (s['service_charge'] or 0)}"
    f" ({s['category']})"
    for s in services
]
chosen_idx = st.selectbox(
    "Select a service",
    options=list(range(len(services))),
    format_func=lambda i: service_labels[i],
    index=default_idx,
)
service = services[chosen_idx]
total_fee = (service["govt_fee"] or 0) + (service["service_charge"] or 0)

with st.container(border=True):
    st.markdown(
        f'<div style="display:flex; align-items:center; '
        f'justify-content:space-between; gap:0.6rem; margin-bottom:0.5rem;">'
        f'{category_badge(service["category"])}'
        f'<span style="color:{MUTED}; font-size:0.85rem; font-weight:500;">'
        f'⏱️ {service["eta_hours"]}h</span>'
        f'</div>'
        f'<div style="font-size:1.05rem; font-weight:700; color:{INK}; '
        f'margin-bottom:0.3rem;">{service["name"]}</div>'
        f'<p style="color:{MUTED}; font-size:0.88rem; line-height:1.55; '
        f'margin:0 0 0.7rem;">{service.get("description") or ""}</p>',
        unsafe_allow_html=True,
    )
    info_cols = st.columns(3)
    info_cols[0].metric("Govt fee", f"₹{service.get('govt_fee') or 0}")
    info_cols[1].metric("Service charge", f"₹{service.get('service_charge') or 0}")
    info_cols[2].metric("ETA", f"{service.get('eta_hours') or 0}h")
    if service.get("requirements"):
        st.markdown(
            f"<div style='margin-top:0.7rem; font-size:0.82rem; "
            f"color:{INK}; font-weight:600;'>Documents required</div>"
            f"<div style='color:{MUTED}; font-size:0.85rem; margin-top:0.2rem;'>"
            f"{service['requirements']}</div>",
            unsafe_allow_html=True,
        )


# ── Personal Details + Upload form ──────────────────────────────────────────
st.markdown("<div style='height:1.2rem;'></div>", unsafe_allow_html=True)
subhead("Personal Details")

with st.form("booking_form", clear_on_submit=False):
    c1, c2 = st.columns(2)
    name = c1.text_input("Full name", placeholder="As per ID proof")
    phone = c2.text_input(
        "Mobile number",
        placeholder="+91 98765 43210",
        max_chars=10,
        help="10-digit Indian mobile, no country code.",
    )

    email = st.text_input(
        "Email (optional)",
        placeholder="we'll email your receipt here",
    )
    notes = st.text_area(
        "Notes for the shop owner (optional)",
        placeholder="Anything specific we should know — urgency, preferred "
                    "pickup time…",
        height=80,
    )

    st.markdown(
        "<div style='height:0.8rem;'></div>", unsafe_allow_html=True,
    )
    subhead("Documents")
    st.caption(
        "Every photo you upload runs through our **AI document checker** "
        "the moment it lands here. We look for sharpness, lighting, and "
        "card framing so you don't get a rejection later. PDFs are "
        "accepted as-is."
    )
    uploaded = st.file_uploader(
        "Upload supporting documents (optional, up to 5)",
        type=["pdf", "jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="You can also bring originals to the shop. Max 10 MB per file.",
        label_visibility="collapsed",
    )

    # ── AI document checker — runs on every uploaded file ────────────
    # Runs INSIDE the form (so the verdict appears immediately on
    # selection) but the actual booking submit + storage upload happens
    # below, only when the form's submit button is clicked.
    expected_ratio = aspect_ratio_for_category(service["category"])
    expected_type = expected_document_type_for_service(
        service_name=service.get("name", ""),
        category=service.get("category", ""),
    )
    blocker_filenames: list[str] = []
    checked_files: list[tuple] = []  # (uploaded_file, report, raw_bytes)
    if uploaded:
        st.markdown(
            "<div style='height:0.6rem;'></div>"
            "<div style='display:flex; align-items:center; gap:0.5rem; "
            "margin-bottom:0.5rem;'>"
            "<span style='display:inline-flex; align-items:center; "
            "gap:0.35rem; background:#DBEAFE; color:#1D4ED8; "
            "padding:0.18rem 0.55rem; border-radius:999px; font-size:0.7rem; "
            "font-weight:700; text-transform:uppercase; letter-spacing:"
            "0.06em;'>\u2728 AI checker</span>"
            "<span style='color:#64748B; font-size:0.84rem;'>"
            "Verifying every file you uploaded \u2014 results below.</span>"
            "</div>",
            unsafe_allow_html=True,
        )

        for upload in uploaded:
            try:
                upload.seek(0)
                data = upload.read()
                upload.seek(0)
            except Exception as exc:  # noqa: BLE001
                st.error(f"Could not read {upload.name}: {exc}")
                continue

            report = check_document(
                file_bytes=data,
                file_name=upload.name,
                expected_aspect_ratio=expected_ratio,
                expected_document_type=expected_type,
            )
            checked_files.append((upload, report, data))
            st.markdown(
                render_report_html(report, file_label=upload.name),
                unsafe_allow_html=True,
            )
            if not report.is_valid:
                blocker_filenames.append(upload.name)

    submitted = st.form_submit_button(
        "Submit booking \u2192",
        use_container_width=True,
        type="primary",
        disabled=bool(blocker_filenames),
    )

    if blocker_filenames:
        st.error(
            "Please replace or remove the file(s) that failed AI checks "
            "before submitting: " + ", ".join(blocker_filenames)
        )


# ── Submission handler ──────────────────────────────────────────────────────
if submitted:
    errors: list[str] = []
    if not name.strip():
        errors.append("Please enter your full name.")
    if not phone.strip():
        errors.append("Please enter your mobile number.")
    elif not PHONE_RE.match(phone.strip()):
        errors.append(
            "Mobile number must be a 10-digit Indian number starting with "
            "6, 7, 8, or 9."
        )
    if uploaded and len(uploaded) > 5:
        errors.append("You can upload at most 5 files per booking.")

    if errors:
        for e in errors:
            st.error(e)
        st.stop()

    booking_id, token = create_booking(
        service_id=service["id"],
        customer_name=name,
        customer_phone=phone,
        customer_email=email or None,
        notes=notes or None,
    )

    saved_docs: list[str] = []
    # Reuse the bytes we already read for the AI checker so we don't
    # double-read the upload buffer (Streamlit's UploadedFile resets its
    # cursor to start after read(), but pulling from our cache is faster
    # and works even when the cursor is mid-stream).
    file_data_by_name = {
        u.name: data for (u, _r, data) in checked_files
    }
    for upload in uploaded or []:
        try:
            data = file_data_by_name.get(upload.name)
            if data is None:
                upload.seek(0)
                data = upload.read()
            save_document(
                booking_id,
                file_name=upload.name,
                file_bytes=data,
                file_type=upload.type,
            )
            saved_docs.append(upload.name)
        except Exception as exc:
            st.warning(f"Could not save {upload.name}: {exc}")

    # Mark step 3 active (purely visual on next interaction)
    st.session_state["c2s_book_step"] = 3
    st.session_state.pop("selected_service_id", None)
    if "service" in st.query_params:
        del st.query_params["service"]

    extra = (
        f"{len(saved_docs)} file(s) uploaded: " + ", ".join(saved_docs)
        if saved_docs else ""
    )
    st.markdown(
        success_token_card(
            token=token,
            total_fee=total_fee,
            eta_hours=service["eta_hours"],
            extra_note=extra,
        ),
        unsafe_allow_html=True,
    )

    # ── Send the booking number to the customer's phone + email ─────
    # Three best-effort channels, all non-blocking. The booking row is
    # already committed at this point, so any messaging failure here
    # never undoes the booking — we just surface what worked / what
    # didn't on the page so the owner can follow up if needed.
    confirmations: list[str] = []
    failures: list[str] = []
    shop_cfg = get_shop_config() or {}
    shop_display_name = (
        (shop_cfg.get("shop_name") or "").strip() or "Click2Serve"
    )
    business_url = (shop_cfg.get("business_url") or "").strip()
    track_url = f"{business_url}/track" if business_url else None
    pay_url = f"{business_url}/pay" if business_url else None

    # 1. WhatsApp via Twilio (auto, paid) — only fires when toggle is on.
    try:
        ok_wa, reason_wa = notify_customer_booking_confirmation_twilio(
            customer_phone=phone,
            customer_name=name,
            token=token,
            service_name=service["name"],
            total_fee=total_fee,
            eta_hours=int(service["eta_hours"] or 0),
        )
    except Exception as exc:  # noqa: BLE001
        ok_wa, reason_wa = False, f"unexpected: {exc}"
    if ok_wa:
        confirmations.append("📲 WhatsApp sent to your phone")
    elif reason_wa and not (
        "disabled" in reason_wa or "not configured" in reason_wa
    ):
        # Surface real Twilio failures but stay quiet for the
        # 'toggle off / no creds' cases — those are normal here.
        failures.append(f"WhatsApp: {reason_wa}")

    # 2. SMS via Twilio (auto, paid, India: requires DLT registration)
    # Sits between WhatsApp and email so the success toast lists the
    # most direct delivery first. Behaves identically to the WhatsApp
    # branch — silent for 'disabled / not configured', surfaces real
    # Twilio errors (DLT block, geo permission, invalid sender, etc.)
    # so the owner can act on them.
    try:
        ok_sms, reason_sms = notify_customer_booking_confirmation_sms(
            customer_phone=phone,
            customer_name=name,
            token=token,
            service_name=service["name"],
            total_fee=total_fee,
            eta_hours=int(service["eta_hours"] or 0),
        )
    except Exception as exc:  # noqa: BLE001
        ok_sms, reason_sms = False, f"unexpected: {exc}"
    if ok_sms:
        confirmations.append("✉️ SMS sent to your phone")
    elif reason_sms and not (
        "disabled" in reason_sms or "not configured" in reason_sms
    ):
        failures.append(f"SMS: {reason_sms}")

    # 3. Email confirmation (auto when configured + customer gave email)
    if email:
        try:
            ok_em, reason_em = send_booking_email(
                to_email=email,
                customer_name=name,
                token=token,
                service_name=service["name"],
                total_fee=total_fee,
                eta_hours=int(service["eta_hours"] or 0),
                shop_name=shop_display_name,
                track_url=track_url,
                pay_url=pay_url,
            )
        except Exception as exc:  # noqa: BLE001
            ok_em, reason_em = False, f"unexpected: {exc}"
        if ok_em:
            confirmations.append(f"📧 Email sent to {email}")
        elif "not configured" in (reason_em or ""):
            # Owner hasn't set up SMTP — silent (covered by Settings tip).
            pass
        else:
            failures.append(f"Email: {reason_em}")

    # 4. Always-available wa.me click-to-chat link — works for ANY phone
    # without API setup. Lands the message into WhatsApp on the
    # customer's device pre-filled, ready to send.
    chat_url = customer_booking_confirmation_chat_url(
        customer_phone=phone,
        customer_name=name,
        token=token,
        service_name=service["name"],
        total_fee=total_fee,
        eta_hours=int(service["eta_hours"] or 0),
    )

    if confirmations:
        st.markdown(
            "<div style='height:0.6rem;'></div>", unsafe_allow_html=True,
        )
        st.success("Confirmation sent — " + " · ".join(confirmations))
    if failures:
        with st.expander("Some confirmations could not be sent"):
            for f in failures:
                st.warning(f)
            st.caption(
                "Your booking is saved either way. Use the WhatsApp button "
                "below if you want a copy on your phone right now."
            )

    # Always offer the manual WhatsApp send — works regardless of Twilio
    # / SMTP configuration. One tap opens WhatsApp on the customer's
    # device with the message ready to send.
    if chat_url:
        st.markdown(
            "<div style='height:0.4rem;'></div>", unsafe_allow_html=True,
        )
        st.link_button(
            f"📲 Send my booking number to WhatsApp ({phone})",
            chat_url,
            use_container_width=True,
        )

    # Pre-fill the pay/track pages with this token
    st.session_state["pay_token"] = token
    st.session_state["pay_phone"] = phone

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
    cta_a, cta_b = st.columns(2)
    cta_a.page_link("pages/pay.py", label="Pay online now →",
                    use_container_width=True)
    cta_b.page_link("pages/track.py", label="Track this booking",
                    use_container_width=True)
