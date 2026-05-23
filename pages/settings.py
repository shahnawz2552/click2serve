"""Owner settings — shop info + UPI payment configuration."""
from __future__ import annotations

import streamlit as st

from core.db import get_shop_config, update_shop_config
from core.payments import is_valid_vpa
from core.styles import inject_global_css, section_header

inject_global_css()

if not st.session_state.get("logged_in"):
    st.warning("Please sign in to access settings.")
    st.page_link("pages/login.py", label="→ Owner login", use_container_width=True)
    st.stop()

section_header(
    eyebrow="Owner · Settings",
    title="Shop &amp; payment settings",
    subtitle="Configure your shop info and the UPI ID that customers will pay to.",
)

shop = get_shop_config()

st.markdown("### Shop information")
with st.form("shop_info"):
    c1, c2 = st.columns(2)
    shop_name = c1.text_input("Shop name", value=shop["shop_name"] or "Click2Serve")
    owner_name = c2.text_input("Owner name", value=shop["owner_name"] or "")

    c3, c4 = st.columns(2)
    owner_phone = c3.text_input("Contact number",
                                value=shop["owner_phone"] or "",
                                placeholder="10-digit mobile")
    opening_hours = c4.text_input("Opening hours",
                                  value=shop["opening_hours"] or "",
                                  placeholder="e.g. 9:00 AM – 9:00 PM")

    address = st.text_area("Shop address",
                           value=shop["address"] or "", height=80,
                           placeholder="Full address shown to customers on their receipt.")

    save_info = st.form_submit_button("💾 Save shop info", type="primary",
                                      use_container_width=True)

if save_info:
    update_shop_config(
        shop_name=shop_name, owner_name=owner_name,
        owner_phone=owner_phone, opening_hours=opening_hours,
        address=address,
    )
    st.success("Shop information updated.")
    st.rerun()

st.markdown("---")
st.markdown("### 💳 Online payments (UPI)")
st.caption(
    "Customers will scan a QR code that pays your UPI ID directly. "
    "After they pay they paste the UTR back into the app for you to verify."
)

current_vpa = shop["upi_vpa"] or ""
current_payee = shop["upi_payee_name"] or shop["shop_name"] or ""

if current_vpa and is_valid_vpa(current_vpa):
    st.success(f"✅ Online payments are **enabled**. Customers will pay to `{current_vpa}`.")
else:
    st.info("ℹ️ Online payments are **not configured yet**. "
            "Add your UPI ID below to enable the customer pay page.")

with st.form("upi_form"):
    upi_vpa = st.text_input(
        "UPI ID (VPA) *",
        value=current_vpa,
        placeholder="e.g. yourname@okaxis  ·  shop@upi  ·  9876543210@ybl",
        help="Find your UPI ID inside PhonePe / GPay / Paytm under 'My UPI' "
             "or 'Bank Account → Manage UPI ID'.",
    )
    upi_payee_name = st.text_input(
        "Payee name (shown to customer)",
        value=current_payee,
        placeholder="e.g. Click2Serve Bharatpur",
    )
    save_upi = st.form_submit_button("💾 Save UPI settings",
                                     type="primary", use_container_width=True)

if save_upi:
    if upi_vpa and not is_valid_vpa(upi_vpa):
        st.error(
            "That doesn't look like a valid UPI ID. "
            "It must be in the format `name@bank`, e.g. `yourname@okaxis`."
        )
    else:
        update_shop_config(upi_vpa=upi_vpa, upi_payee_name=upi_payee_name)
        st.success("UPI settings saved. The customer pay page is now live.")
        st.rerun()

st.markdown("---")
with st.expander("🚀 Want auto-reconciled payments? (Razorpay roadmap)"):
    st.markdown(
        """
        The current UPI flow needs you to confirm each UTR manually in your
        UPI app. For fully automatic reconciliation:

        1. Sign up at https://razorpay.com (free, requires business KYC).
        2. Generate API keys in Dashboard → Settings → API Keys.
        3. Add them to `.streamlit/secrets.toml`:

           ```toml
           [razorpay]
           key_id = "rzp_test_xxxxxxxxxxxxxx"
           key_secret = "your-secret"
           ```

        4. The repo's roadmap includes a Razorpay Payment Links integration
           that drops in here without changing the data model.
        """
    )
