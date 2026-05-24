"""First-run seed data: 12 default services + a default admin user.

Idempotent — safe to call repeatedly. Only inserts when the target
table is empty so re-runs don't create duplicates.
"""
from __future__ import annotations

import logging

from .db import get_supabase

logger = logging.getLogger(__name__)


DEFAULT_SERVICES: list[dict] = [
    # Government IDs
    {"name": "New Passport Application", "category": "Government IDs",
     "description": "End-to-end assistance for fresh passport applications including form filling, document verification, and appointment booking on Passport Seva portal.",
     "govt_fee": 1500, "service_charge": 200, "eta_hours": 48,
     "requirements": "Aadhaar card, address proof, birth certificate, recent passport-size photo, parent's documents (for minors)."},
    {"name": "Passport Renewal / Re-issue", "category": "Government IDs",
     "description": "Renewal of expiring or expired passports with form re-issue and slot booking.",
     "govt_fee": 1500, "service_charge": 200, "eta_hours": 48,
     "requirements": "Old passport, Aadhaar card, address proof, recent photograph."},
    {"name": "Aadhaar Update / Correction", "category": "Government IDs",
     "description": "Update name, address, date of birth, mobile number or photograph in Aadhaar.",
     "govt_fee": 50, "service_charge": 100, "eta_hours": 24,
     "requirements": "Existing Aadhaar card, supporting document for the field being updated."},
    {"name": "PAN Card Application", "category": "Government IDs",
     "description": "Fresh PAN card application or correction in existing PAN.",
     "govt_fee": 110, "service_charge": 150, "eta_hours": 72,
     "requirements": "Aadhaar card, recent passport-size photograph, signature."},
    {"name": "Voter ID Registration", "category": "Government IDs",
     "description": "New voter ID registration or correction in existing card via NVSP portal.",
     "govt_fee": 0, "service_charge": 100, "eta_hours": 48,
     "requirements": "Aadhaar card, address proof, recent photograph, age proof."},

    # Vehicle Services
    {"name": "Driving License Application", "category": "Vehicle Services",
     "description": "New learner's licence or permanent driving licence application via Parivahan portal.",
     "govt_fee": 700, "service_charge": 200, "eta_hours": 48,
     "requirements": "Aadhaar card, address proof, age proof, recent photograph, learner's licence (for permanent DL)."},
    {"name": "Driving License Renewal", "category": "Vehicle Services",
     "description": "Renewal of expiring or expired driving licence.",
     "govt_fee": 400, "service_charge": 150, "eta_hours": 24,
     "requirements": "Existing DL, Aadhaar card, recent photograph."},
    {"name": "Traffic Challan Payment", "category": "Vehicle Services",
     "description": "Look up and pay e-challans on the Parivahan / state e-challan portal.",
     "govt_fee": 0, "service_charge": 50, "eta_hours": 1,
     "requirements": "Vehicle number or challan number, driving licence (if challan is on DL)."},

    # Bill Payments
    {"name": "Electricity Bill Payment", "category": "Bill Payments",
     "description": "Pay electricity bills for any state DISCOM via Bharat BillPay.",
     "govt_fee": 0, "service_charge": 30, "eta_hours": 1,
     "requirements": "Latest bill or consumer number."},
    {"name": "Gas / Water / DTH Bill", "category": "Bill Payments",
     "description": "Pay LPG booking, water utility bills, DTH recharges and broadband bills.",
     "govt_fee": 0, "service_charge": 30, "eta_hours": 1,
     "requirements": "Bill / customer ID for the relevant service."},

    # Document Services
    {"name": "Photocopy / Print / Scan", "category": "Document Services",
     "description": "Black & white or colour photocopying, printing from soft copy, scanning to PDF, lamination.",
     "govt_fee": 0, "service_charge": 5, "eta_hours": 1,
     "requirements": "Original document or soft copy on USB / WhatsApp / email."},
    {"name": "Passport-size Photo", "category": "Document Services",
     "description": "Set of 8 passport-size photographs printed on photo paper.",
     "govt_fee": 0, "service_charge": 100, "eta_hours": 1,
     "requirements": "Walk-in for photo capture or share digital photo."},
]


def seed_services_if_empty() -> None:
    try:
        sb = get_supabase()
        res = sb.table("services").select("id", count="exact").limit(1).execute()
        if (res.count or 0) > 0:
            return
        # Mark all default rows active=true for the initial seed
        rows = [{**s, "active": True} for s in DEFAULT_SERVICES]
        sb.table("services").insert(rows).execute()
    except Exception as exc:
        logger.warning("seed_services_if_empty skipped: %s", exc)


def seed_default_admin_if_empty() -> None:
    """Create the default admin if no users exist."""
    from datetime import datetime, timezone

    from .auth import (
        DEFAULT_ADMIN_PASSWORD, DEFAULT_ADMIN_USERNAME, hash_password,
    )

    try:
        sb = get_supabase()
        res = sb.table("users").select("id", count="exact").limit(1).execute()
        if (res.count or 0) > 0:
            return
        sb.table("users").insert({
            "username": DEFAULT_ADMIN_USERNAME,
            "password_hash": hash_password(DEFAULT_ADMIN_PASSWORD),
            "role": "owner",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }).execute()
    except Exception as exc:
        logger.warning("seed_default_admin_if_empty skipped: %s", exc)
