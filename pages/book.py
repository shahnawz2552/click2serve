"""Customer booking form — pick service, fill details, upload docs, get token."""
from __future__ import annotations

import re

import streamlit as st

from core.db import create_booking, get_service, list_services, save_document
from core.styles import inject_global_css, section_header

inject_global_css()

PHONE_RE = re.compile(r"^[6-9]\d{9}$")  # Indian mobile pattern; relax if needed


section_header(
    eyebrow="Book a service",
    title="Tell us what you need.",
    subtitle="Fill in your details — you'll receive a token number to track your booking.",
)

services = list_services(active_only=True)
if not services:
    st.error("No services are currently available. Please check back later.")
    st.stop()

# Pre-select if user came from a service card on the home page —
# either via st.query_params (?service=ID) or session_state.
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

service_labels = [
    f"{s['name']} — ₹{s['govt_fee'] + s['service_charge']} ({s['category']})"
    for s in services
]
chosen_idx = st.selectbox(
    "Select a service",
    options=list(range(len(services))),
    format_func=lambda i: service_labels[i],
    index=default_idx,
)
service = services[chosen_idx]
total_fee = service["govt_fee"] + service["service_charge"]

with st.container(border=True):
    st.markdown(
        f"<div class='c2s-cat'>{service['category']}</div>"
        f"<div class='c2s-svc-name' style='font-size:1.4rem;'>{service['name']}</div>",
        unsafe_allow_html=True,
    )
    st.markdown(
        f"<p style='color:#5A6157; line-height:1.55; margin:0.4rem 0 1rem;'>"
        f"{service['description']}</p>",
        unsafe_allow_html=True,
    )
    info_cols = st.columns(3)
    info_cols[0].metric("Government fee", f"₹{service['govt_fee']}")
    info_cols[1].metric("Service charge", f"₹{service['service_charge']}")
    info_cols[2].metric("Estimated time", f"{service['eta_hours']}h")
    if service["requirements"]:
        st.markdown(
            "<div style='margin-top:1rem;'><b>Documents required</b></div>",
            unsafe_allow_html=True,
        )
        st.info(service["requirements"])

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)
st.markdown(
    "<h3 style='margin-bottom:1rem;'>Your details</h3>",
    unsafe_allow_html=True,
)

with st.form("booking_form", clear_on_submit=False):
    c1, c2 = st.columns(2)
    name = c1.text_input("Full name", placeholder="As per ID proof")
    phone = c2.text_input("Mobile number", placeholder="10-digit mobile",
                          max_chars=10)

    email = st.text_input(
        "Email (optional)",
        placeholder="we'll email your receipt here",
    )
    notes = st.text_area(
        "Notes for the shop owner (optional)",
        placeholder="Anything specific we should know — e.g. urgency, preferred pickup time...",
        height=80,
    )

    uploaded = st.file_uploader(
        "Upload supporting documents (optional, up to 5)",
        type=["pdf", "jpg", "jpeg", "png", "webp"],
        accept_multiple_files=True,
        help="You can also bring originals to the shop. Max 10 MB per file.",
    )

    submitted = st.form_submit_button("Submit booking →",
                                      use_container_width=True,
                                      type="primary")

if submitted:
    errors: list[str] = []
    if not name.strip():
        errors.append("Please enter your full name.")
    if not phone.strip():
        errors.append("Please enter your mobile number.")
    elif not PHONE_RE.match(phone.strip()):
        errors.append(
            "Mobile number must be a 10-digit Indian number starting with 6/7/8/9."
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

    # Clear pre-selection so a fresh booking starts clean
    st.session_state.pop("selected_service_id", None)
    if "service" in st.query_params:
        del st.query_params["service"]

    st.success("Booking confirmed.")
    with st.container(border=True):
        st.markdown(
            f"<div class='c2s-cat'>Your token</div>"
            f"<div style='font-size:2.4rem; font-weight:900; "
            f"letter-spacing:-0.04em; color:#0E120F; line-height:1;'>"
            f"{token}</div>",
            unsafe_allow_html=True,
        )
        st.caption(
            "Save this token — you'll need it to track or pick up your service."
        )
        col1, col2 = st.columns(2)
        col1.metric("Total fee", f"₹{total_fee}")
        col2.metric("Estimated ready in", f"{service['eta_hours']}h")
        if saved_docs:
            st.markdown(
                f"<div style='margin-top:0.8rem; color:#5A6157;'>"
                f"<b>{len(saved_docs)}</b> file(s) uploaded: "
                + ", ".join(saved_docs) + "</div>",
                unsafe_allow_html=True,
            )
        st.info(
            "You can pay online now via UPI, or pay in cash at the shop "
            "when you pick up your work."
        )

    # Pre-fill the pay page so the customer doesn't have to retype their token
    st.session_state["pay_token"] = token
    st.session_state["pay_phone"] = phone

    cta_a, cta_b = st.columns(2)
    cta_a.page_link("pages/pay.py",
                    label="Pay online now →",
                    use_container_width=True)
    cta_b.page_link("pages/track.py",
                    label="Track this booking",
                    use_container_width=True)
