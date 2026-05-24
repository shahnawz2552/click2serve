"""Customer booking form — pick service, fill details, upload docs, get token.

Three logical steps shown as a progress bar:
    1. Details      (service + personal info)
    2. Upload       (supporting documents)
    3. Confirm      (submit + receive token)

In Streamlit's single-page model these are all on one page; the bar is a
visual cue. Step 1+2 are highlighted before submit, step 3 after.
"""
from __future__ import annotations

import re

import streamlit as st

from core.db import create_booking, list_services, save_document
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
    info_cols[0].metric("Govt fee", f"₹{service['govt_fee']}")
    info_cols[1].metric("Service charge", f"₹{service['service_charge']}")
    info_cols[2].metric("ETA", f"{service['eta_hours']}h")
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
    uploaded = st.file_uploader(
        "Upload supporting documents (optional, up to 5)",
        type=["pdf", "jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="You can also bring originals to the shop. Max 10 MB per file.",
        label_visibility="collapsed",
    )

    submitted = st.form_submit_button("Submit booking →",
                                      use_container_width=True,
                                      type="primary")


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
    for upload in uploaded or []:
        try:
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

    # Pre-fill the pay/track pages with this token
    st.session_state["pay_token"] = token
    st.session_state["pay_phone"] = phone

    st.markdown("<div style='height:1rem;'></div>", unsafe_allow_html=True)
    cta_a, cta_b = st.columns(2)
    cta_a.page_link("pages/pay.py", label="Pay online now →",
                    use_container_width=True)
    cta_b.page_link("pages/track.py", label="Track this booking",
                    use_container_width=True)
