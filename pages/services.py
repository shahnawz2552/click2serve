"""Owner — service catalogue CRUD.

Lists every service (active + soft-deleted), lets the owner add a new one,
edit any field on an existing one, or soft-delete by toggling ``active``.
We never hard-delete a service because historical bookings reference it.
"""
from __future__ import annotations

import pandas as pd
import streamlit as st

from core.db import (
    create_service, list_services, soft_delete_service, update_service,
)
from core.styles import inject_global_css, section_header

inject_global_css()

if not st.session_state.get("logged_in"):
    st.warning("Please sign in to manage services.")
    st.page_link("pages/login.py", label="Owner login →",
                 use_container_width=True)
    st.stop()

section_header(
    eyebrow="Owner · Catalogue",
    title="Services.",
    subtitle="Add, edit, or retire the services your shop offers. "
             "Disabled services keep their booking history but are hidden "
             "from customers.",
)

# ── Listing ─────────────────────────────────────────────────────────────────
all_services = list_services(active_only=False)

if all_services:
    df = pd.DataFrame([
        {
            "ID": s["id"],
            "Name": s["name"],
            "Category": s["category"],
            "Govt fee (₹)": s["govt_fee"],
            "Service charge (₹)": s["service_charge"],
            "ETA (h)": s["eta_hours"],
            "Active": s.get("active", True),
        }
        for s in all_services
    ])
    st.dataframe(df, use_container_width=True, hide_index=True)
else:
    st.info("No services yet. Add the first one below.")

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)

# ── Add a new service ───────────────────────────────────────────────────────
st.markdown(
    "<div class='c2s-cat'>Section 01</div>"
    "<h3 style='margin:0 0 1rem;'>Add a new service.</h3>",
    unsafe_allow_html=True,
)

existing_categories = sorted({s["category"] for s in all_services}) or [
    "Government IDs", "Vehicle Services", "Bill Payments", "Document Services",
]

with st.form("add_service", clear_on_submit=True):
    c1, c2 = st.columns([2, 1])
    new_name = c1.text_input("Service name", placeholder="e.g. PAN Correction")
    new_category = c2.selectbox(
        "Category", existing_categories + ["+ New category"], index=0,
    )
    if new_category == "+ New category":
        new_category = st.text_input("New category name")

    new_description = st.text_area(
        "Description (shown to customers)",
        placeholder="One sentence about what's included…",
        height=70,
    )
    new_requirements = st.text_area(
        "Documents / requirements",
        placeholder="What customers need to bring or upload…",
        height=70,
    )

    fc1, fc2, fc3, fc4 = st.columns(4)
    new_govt_fee = fc1.number_input("Govt fee (₹)", min_value=0, value=0, step=50)
    new_service_charge = fc2.number_input(
        "Service charge (₹)", min_value=0, value=100, step=10,
    )
    new_eta_hours = fc3.number_input(
        "ETA (hours)", min_value=1, value=24, step=1,
    )
    new_active = fc4.checkbox("Active", value=True)

    add = st.form_submit_button("Add service →", type="primary",
                                use_container_width=True)

if add:
    if not new_name.strip():
        st.error("Name is required.")
    elif not new_category.strip():
        st.error("Category is required.")
    elif any(s["name"].lower() == new_name.strip().lower()
             for s in all_services):
        st.error(f"A service named '{new_name.strip()}' already exists.")
    else:
        create_service(
            name=new_name,
            category=new_category,
            description=new_description,
            govt_fee=int(new_govt_fee),
            service_charge=int(new_service_charge),
            eta_hours=int(new_eta_hours),
            requirements=new_requirements,
            active=bool(new_active),
        )
        st.success(f"Added '{new_name.strip()}'.")
        st.rerun()

st.markdown("<hr class='c2s-rule'/>", unsafe_allow_html=True)

# ── Edit / disable an existing service ─────────────────────────────────────
st.markdown(
    "<div class='c2s-cat'>Section 02</div>"
    "<h3 style='margin:0 0 1rem;'>Edit a service.</h3>",
    unsafe_allow_html=True,
)

if not all_services:
    st.caption("Add at least one service above first.")
    st.stop()

labels = {
    s["id"]: f"{s['name']}  —  ₹{s['govt_fee'] + s['service_charge']}  "
             f"({'active' if s.get('active') else 'disabled'})"
    for s in all_services
}
edit_id = st.selectbox(
    "Pick a service to edit",
    options=list(labels.keys()),
    format_func=lambda i: labels[i],
)
target = next(s for s in all_services if s["id"] == edit_id)

with st.form("edit_service"):
    e_name = st.text_input("Service name", value=target["name"])
    e_category = st.text_input("Category", value=target["category"])
    e_description = st.text_area(
        "Description", value=target.get("description") or "", height=70,
    )
    e_requirements = st.text_area(
        "Documents / requirements",
        value=target.get("requirements") or "", height=70,
    )
    fc1, fc2, fc3, fc4 = st.columns(4)
    e_govt_fee = fc1.number_input(
        "Govt fee (₹)", min_value=0, value=int(target["govt_fee"] or 0),
        step=50,
    )
    e_service_charge = fc2.number_input(
        "Service charge (₹)", min_value=0,
        value=int(target["service_charge"] or 0), step=10,
    )
    e_eta_hours = fc3.number_input(
        "ETA (hours)", min_value=1,
        value=int(target["eta_hours"] or 1), step=1,
    )
    e_active = fc4.checkbox("Active", value=bool(target.get("active", True)))

    btn_save, btn_disable = st.columns([1, 1])
    save = btn_save.form_submit_button(
        "Save changes →", type="primary", use_container_width=True,
    )
    disable = btn_disable.form_submit_button(
        "Disable (soft delete)", use_container_width=True,
    )

if save:
    if not e_name.strip() or not e_category.strip():
        st.error("Name and category are required.")
    else:
        update_service(
            edit_id,
            name=e_name,
            category=e_category,
            description=e_description,
            govt_fee=int(e_govt_fee),
            service_charge=int(e_service_charge),
            eta_hours=int(e_eta_hours),
            requirements=e_requirements,
            active=bool(e_active),
        )
        st.success("Service updated.")
        st.rerun()

if disable:
    soft_delete_service(edit_id)
    st.warning(
        f"'{target['name']}' is now disabled. Existing bookings still work; "
        "the service is just hidden from customers."
    )
    st.rerun()
