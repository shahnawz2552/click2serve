"""Supabase data layer for Click2Serve.

Replaces the previous SQLite-based persistence. Every query goes through
``supabase-py`` (the official Postgres + Storage SDK).

Setup checklist:
    1. Create a Supabase project at https://supabase.com.
    2. In the SQL editor, run ``supabase/schema.sql`` once.
    3. In Storage, create a private bucket named ``click2serve-documents``.
    4. Copy the project URL + anon key into ``.streamlit/secrets.toml``.
       See ``.streamlit/secrets.toml.example`` for the template.

The public function surface is a drop-in replacement for the previous
sqlite version, so pages don't need to change. Functions return plain
dicts (which behave like the old ``sqlite3.Row`` for ``row['key']`` access).
"""
from __future__ import annotations

import logging
import secrets as secrets_lib
from datetime import date, datetime, timezone
from typing import Any

import streamlit as st
from supabase import Client, create_client

logger = logging.getLogger(__name__)

STATUSES = ["Pending", "In Progress", "Ready", "Delivered", "Cancelled"]
PAYMENT_METHODS = ["Unpaid", "Cash", "UPI", "Card"]


# ──────────────────────────────────────────────────────────────────────────────
# Client + secrets
# ──────────────────────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner=False)
def get_supabase() -> Client:
    """Return a cached Supabase client built from Streamlit secrets."""
    url= st.secrets("SUPABASE_URL")
    #url = (cfg.get("url") or "").strip()
    #key = (cfg.get("key") or cfg.get("anon_key") or "").strip()
    key = st.secrets("SUPABASE_KEY")
    return create_client(url, key)

def _bucket() -> str:
    cfg = st.secrets.get("supabase", {}) if hasattr(st, "secrets") else {}
    return (cfg.get("storage_bucket") or "click2serve-documents").strip()


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def init_db() -> None:
    """Verify the connection and seed default services + admin user.

    Note: supabase-py cannot run DDL through PostgREST, so the schema must
    already exist. This function only seeds reference rows.
    """
    try:
        sb = get_supabase()
        # Light sanity check that we can reach the project.
        sb.table("services").select("id").limit(1).execute()
    except Exception as exc:
        logger.warning("init_db: Supabase ping failed: %s", exc)
        return

    # Singleton shop_config row
    try:
        sb.table("shop_config").upsert(
            {"id": 1, "updated_at": _now_iso()},
            on_conflict="id",
            ignore_duplicates=True,
        ).execute()
    except Exception as exc:
        logger.warning("init_db: shop_config seed skipped: %s", exc)

    # Defer to seed module (services + default admin)
    from .seed import seed_default_admin_if_empty, seed_services_if_empty

    seed_services_if_empty()
    seed_default_admin_if_empty()


# ──────────────────────────────────────────────────────────────────────────────
# Services
# ──────────────────────────────────────────────────────────────────────────────
def list_services(active_only: bool = True) -> list[dict[str, Any]]:
    sb = get_supabase()
    q = sb.table("services").select("*")
    if active_only:
        q = q.eq("active", True)
    res = q.order("category").order("name").execute()
    return res.data or []


def get_service(service_id: int) -> dict[str, Any] | None:
    sb = get_supabase()
    res = sb.table("services").select("*").eq("id", service_id).limit(1).execute()
    rows = res.data or []
    return rows[0] if rows else None


def list_categories() -> list[str]:
    rows = list_services(active_only=True)
    seen, out = set(), []
    for r in rows:
        if r["category"] not in seen:
            seen.add(r["category"])
            out.append(r["category"])
    return sorted(out)


def create_service(
    *, name: str, category: str, description: str = "",
    govt_fee: int = 0, service_charge: int = 0,
    eta_hours: int = 24, requirements: str = "", active: bool = True,
) -> dict[str, Any]:
    sb = get_supabase()
    res = sb.table("services").insert({
        "name": name.strip(),
        "category": category.strip(),
        "description": description.strip(),
        "govt_fee": int(govt_fee),
        "service_charge": int(service_charge),
        "eta_hours": int(eta_hours),
        "requirements": requirements.strip(),
        "active": bool(active),
    }).execute()
    return (res.data or [{}])[0]


def update_service(service_id: int, **fields: Any) -> None:
    allowed = {
        "name", "category", "description", "govt_fee", "service_charge",
        "eta_hours", "requirements", "active",
    }
    clean = {k: v for k, v in fields.items() if k in allowed}
    if not clean:
        return
    sb = get_supabase()
    sb.table("services").update(clean).eq("id", service_id).execute()


def soft_delete_service(service_id: int) -> None:
    """Set active=False — preserves historical bookings that reference it."""
    sb = get_supabase()
    sb.table("services").update({"active": False}).eq("id", service_id).execute()


# ──────────────────────────────────────────────────────────────────────────────
# Bookings
# ──────────────────────────────────────────────────────────────────────────────
def _new_token() -> str:
    return f"C2S-{secrets_lib.token_hex(2).upper()}"


def create_booking(
    *,
    service_id: int,
    customer_name: str,
    customer_phone: str,
    customer_email: str | None = None,
    notes: str | None = None,
) -> tuple[int, str]:
    """Insert a booking with a unique token. Returns (id, token)."""
    sb = get_supabase()
    now = _now_iso()
    for _ in range(5):
        token = _new_token()
        existing = (
            sb.table("bookings").select("id").eq("token", token).limit(1).execute()
        )
        if not (existing.data or []):
            break
    else:
        token = f"C2S-{secrets_lib.token_hex(4).upper()}"

    res = sb.table("bookings").insert({
        "token": token,
        "service_id": int(service_id),
        "customer_name": customer_name.strip(),
        "customer_phone": customer_phone.strip(),
        "customer_email": (customer_email or "").strip() or None,
        "notes": (notes or "").strip() or None,
        "status": "Pending",
        "payment_method": "Unpaid",
        "payment_status": "unpaid",
        "amount_paid": 0,
        "created_at": now,
        "updated_at": now,
    }).execute()
    row = (res.data or [{}])[0]
    return int(row["id"]), token


def _hydrate_booking(b: dict, sv: dict | None) -> dict:
    """Attach service-derived fields onto a booking dict for views."""
    if sv:
        b["service_name"] = sv["name"]
        b["service_category"] = sv["category"]
        b["govt_fee"] = sv["govt_fee"]
        b["service_charge"] = sv["service_charge"]
        b["eta_hours"] = sv["eta_hours"]
        b["total_fee"] = (sv["govt_fee"] or 0) + (sv["service_charge"] or 0)
    else:
        b.setdefault("service_name", "(unknown)")
        b.setdefault("service_category", "")
        b.setdefault("govt_fee", 0)
        b.setdefault("service_charge", 0)
        b.setdefault("eta_hours", 0)
        b.setdefault("total_fee", 0)
    return b


def _service_lookup(service_ids: list[int]) -> dict[int, dict]:
    if not service_ids:
        return {}
    sb = get_supabase()
    res = (
        sb.table("services")
        .select("*")
        .in_("id", list(set(service_ids)))
        .execute()
    )
    return {row["id"]: row for row in (res.data or [])}


def get_booking_by_token(
    token: str, phone: str | None = None,
) -> dict[str, Any] | None:
    sb = get_supabase()
    q = sb.table("bookings").select("*").ilike("token", token.strip())
    if phone:
        q = q.eq("customer_phone", phone.strip())
    res = q.limit(1).execute()
    rows = res.data or []
    if not rows:
        return None
    b = rows[0]
    svs = _service_lookup([b["service_id"]])
    return _hydrate_booking(b, svs.get(b["service_id"]))


def list_bookings(
    *,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    phone: str | None = None,
    limit: int = 500,
) -> list[dict[str, Any]]:
    sb = get_supabase()
    q = sb.table("bookings").select("*")
    if status and status != "All":
        q = q.eq("status", status)
    if date_from:
        q = q.gte("created_at", f"{date_from.isoformat()}T00:00:00+00:00")
    if date_to:
        q = q.lte("created_at", f"{date_to.isoformat()}T23:59:59+00:00")
    if phone:
        q = q.eq("customer_phone", phone.strip())
    if search:
        like = f"%{search.strip()}%"
        # Postgres OR — supabase-py supports the .or_() string syntax.
        q = q.or_(
            f"token.ilike.{like},customer_name.ilike.{like},customer_phone.ilike.{like}"
        )
    res = q.order("created_at", desc=True).limit(limit).execute()
    rows = res.data or []
    svs = _service_lookup([r["service_id"] for r in rows])
    return [_hydrate_booking(r, svs.get(r["service_id"])) for r in rows]


def update_booking_status(booking_id: int, status: str) -> None:
    if status not in STATUSES:
        raise ValueError(f"Invalid status: {status}")
    sb = get_supabase()
    sb.table("bookings").update(
        {"status": status, "updated_at": _now_iso()}
    ).eq("id", booking_id).execute()


def update_booking_payment(booking_id: int, *, method: str, amount: int) -> None:
    if method not in PAYMENT_METHODS:
        raise ValueError(f"Invalid payment method: {method}")
    payment_status = "unpaid" if method == "Unpaid" else "verified"
    sb = get_supabase()
    sb.table("bookings").update({
        "payment_method": method,
        "amount_paid": int(amount),
        "payment_status": payment_status,
        "updated_at": _now_iso(),
    }).eq("id", booking_id).execute()


# ──────────────────────────────────────────────────────────────────────────────
# Documents — Supabase Storage
# ──────────────────────────────────────────────────────────────────────────────
def save_document(
    booking_id: int, *, file_name: str, file_bytes: bytes,
    file_type: str | None,
) -> str:
    """Upload bytes to the storage bucket and record it. Returns storage key."""
    sb = get_supabase()
    bucket = _bucket()
    safe_name = "".join(
        c for c in (file_name or "file") if c.isalnum() or c in "._- "
    ).strip() or "file"

    # Storage keys are flat strings; namespace by booking id.
    storage_key = f"{booking_id}/{int(datetime.now().timestamp())}_{safe_name}"
    try:
        sb.storage.from_(bucket).upload(
            storage_key,
            file_bytes,
            file_options={"content-type": file_type or "application/octet-stream"},
        )
    except Exception as exc:
        # Bucket might not exist locally — surface a clear error.
        raise RuntimeError(
            f"Failed to upload to Supabase Storage bucket '{bucket}': {exc}. "
            "Ensure the bucket exists and is private."
        ) from exc

    sb.table("documents").insert({
        "booking_id": int(booking_id),
        "file_name": safe_name,
        "file_path": storage_key,
        "file_type": file_type,
        "size_bytes": len(file_bytes),
        "uploaded_at": _now_iso(),
    }).execute()
    return storage_key


def list_documents(booking_id: int) -> list[dict[str, Any]]:
    sb = get_supabase()
    res = (
        sb.table("documents")
        .select("*")
        .eq("booking_id", booking_id)
        .order("uploaded_at")
        .execute()
    )
    return res.data or []


def signed_document_url(storage_key: str, expires_in: int = 600) -> str | None:
    """Return a short-lived signed URL for owner-side viewing."""
    sb = get_supabase()
    try:
        res = sb.storage.from_(_bucket()).create_signed_url(
            storage_key, expires_in
        )
        return res.get("signedURL") or res.get("signed_url")
    except Exception as exc:
        logger.warning("signed_document_url failed: %s", exc)
        return None


# ──────────────────────────────────────────────────────────────────────────────
# Reports — fetch + aggregate locally (small N is fine)
# ──────────────────────────────────────────────────────────────────────────────
def _bookings_in_range(date_from: date, date_to: date) -> list[dict]:
    sb = get_supabase()
    res = (
        sb.table("bookings")
        .select("*")
        .gte("created_at", f"{date_from.isoformat()}T00:00:00+00:00")
        .lte("created_at", f"{date_to.isoformat()}T23:59:59+00:00")
        .execute()
    )
    return res.data or []


def revenue_summary(date_from: date, date_to: date) -> dict[str, Any]:
    rows = _bookings_in_range(date_from, date_to)
    return {
        "total_bookings": len(rows),
        "revenue": sum(int(r.get("amount_paid") or 0) for r in rows),
        "delivered": sum(1 for r in rows if r.get("status") == "Delivered"),
        "cancelled": sum(1 for r in rows if r.get("status") == "Cancelled"),
        "unpaid": sum(1 for r in rows if r.get("payment_method") == "Unpaid"),
    }


def revenue_by_day(date_from: date, date_to: date) -> list[dict[str, Any]]:
    rows = _bookings_in_range(date_from, date_to)
    by_day: dict[str, dict] = {}
    for r in rows:
        day = (r.get("created_at") or "")[:10]
        bucket = by_day.setdefault(day, {"day": day, "bookings": 0, "revenue": 0})
        bucket["bookings"] += 1
        bucket["revenue"] += int(r.get("amount_paid") or 0)
    return [by_day[k] for k in sorted(by_day)]


def revenue_by_service(date_from: date, date_to: date) -> list[dict[str, Any]]:
    rows = _bookings_in_range(date_from, date_to)
    if not rows:
        return []
    svs = _service_lookup([r["service_id"] for r in rows])
    by_svc: dict[str, dict] = {}
    for r in rows:
        sv = svs.get(r["service_id"])
        name = sv["name"] if sv else "(deleted)"
        b = by_svc.setdefault(name, {"service_name": name, "bookings": 0, "revenue": 0})
        b["bookings"] += 1
        b["revenue"] += int(r.get("amount_paid") or 0)
    return sorted(by_svc.values(), key=lambda x: (-x["revenue"], -x["bookings"]))


def today_kpis() -> dict[str, Any]:
    today = date.today()
    rows = _bookings_in_range(today, today)
    return {
        "total":       len(rows),
        "pending":     sum(1 for r in rows if r.get("status") == "Pending"),
        "in_progress": sum(1 for r in rows if r.get("status") == "In Progress"),
        "ready":       sum(1 for r in rows if r.get("status") == "Ready"),
        "delivered":   sum(1 for r in rows if r.get("status") == "Delivered"),
        "revenue":     sum(int(r.get("amount_paid") or 0) for r in rows),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Shop config (singleton)
# ──────────────────────────────────────────────────────────────────────────────
def get_shop_config() -> dict[str, Any]:
    sb = get_supabase()
    res = sb.table("shop_config").select("*").eq("id", 1).limit(1).execute()
    rows = res.data or []
    if rows:
        return rows[0]
    # First-run: create the singleton.
    sb.table("shop_config").insert({"id": 1, "updated_at": _now_iso()}).execute()
    res = sb.table("shop_config").select("*").eq("id", 1).limit(1).execute()
    return (res.data or [{}])[0]


def update_shop_config(**fields: Any) -> None:
    allowed = {
        "shop_name", "owner_name", "owner_phone", "address",
        "upi_vpa", "upi_payee_name", "opening_hours",
    }
    clean = {
        k: (v.strip() if isinstance(v, str) else v)
        for k, v in fields.items() if k in allowed
    }
    if not clean:
        return
    clean["updated_at"] = _now_iso()
    sb = get_supabase()
    sb.table("shop_config").update(clean).eq("id", 1).execute()


# ──────────────────────────────────────────────────────────────────────────────
# Online payment lifecycle
# ──────────────────────────────────────────────────────────────────────────────
def submit_payment_proof(
    booking_id: int, *, ref: str, amount: int, method: str = "UPI",
) -> None:
    sb = get_supabase()
    sb.table("bookings").update({
        "payment_method": method,
        "payment_status": "submitted",
        "payment_ref": ref.strip(),
        "amount_paid": int(amount),
        "updated_at": _now_iso(),
    }).eq("id", booking_id).execute()


def verify_payment(booking_id: int) -> None:
    sb = get_supabase()
    sb.table("bookings").update({
        "payment_status": "verified",
        "updated_at": _now_iso(),
    }).eq("id", booking_id).execute()


def reject_payment(booking_id: int) -> None:
    sb = get_supabase()
    sb.table("bookings").update({
        "payment_status": "rejected",
        "payment_ref": None,
        "payment_method": "Unpaid",
        "amount_paid": 0,
        "updated_at": _now_iso(),
    }).eq("id", booking_id).execute()


def pending_verification_count() -> int:
    sb = get_supabase()
    res = (
        sb.table("bookings")
        .select("id", count="exact")
        .eq("payment_status", "submitted")
        .execute()
    )
    return int(res.count or 0)
