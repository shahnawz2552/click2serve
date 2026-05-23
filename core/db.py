"""SQLite database layer for Click2Serve.

All persistence lives in a single file under ./data/. The schema is created on
first call to `init_db()` and is idempotent, so the app can be redeployed
freely without losing prior data.
"""
from __future__ import annotations

import secrets
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from pathlib import Path
from typing import Any, Iterable

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = DATA_DIR / "click2serve.db"
UPLOAD_DIR = PROJECT_ROOT / "uploads"

STATUSES = ["Pending", "In Progress", "Ready", "Delivered", "Cancelled"]
PAYMENT_METHODS = ["Unpaid", "Cash", "UPI", "Card"]


def _ensure_dirs() -> None:
    DATA_DIR.mkdir(exist_ok=True)
    UPLOAD_DIR.mkdir(exist_ok=True)


def _add_column_if_missing(conn, table: str, column: str, decl: str) -> None:
    """Idempotent ALTER TABLE used for schema migrations on existing DBs."""
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    existing = {r["name"] for r in rows}
    if column not in existing:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {decl}")


@contextmanager
def get_conn():
    """Yield a SQLite connection with FK enforcement and row-as-dict access."""
    _ensure_dirs()
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create tables (idempotent) and seed default services + admin user."""
    _ensure_dirs()
    with get_conn() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS services (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL UNIQUE,
                category TEXT NOT NULL,
                description TEXT NOT NULL,
                govt_fee INTEGER NOT NULL DEFAULT 0,
                service_charge INTEGER NOT NULL DEFAULT 0,
                eta_hours INTEGER NOT NULL DEFAULT 24,
                requirements TEXT NOT NULL DEFAULT '',
                active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS bookings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                token TEXT NOT NULL UNIQUE,
                service_id INTEGER NOT NULL REFERENCES services(id),
                customer_name TEXT NOT NULL,
                customer_phone TEXT NOT NULL,
                customer_email TEXT,
                notes TEXT,
                status TEXT NOT NULL DEFAULT 'Pending',
                payment_method TEXT NOT NULL DEFAULT 'Unpaid',
                payment_status TEXT NOT NULL DEFAULT 'unpaid',
                payment_ref TEXT,
                amount_paid INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS ix_bookings_token ON bookings(token);
            CREATE INDEX IF NOT EXISTS ix_bookings_phone ON bookings(customer_phone);
            CREATE INDEX IF NOT EXISTS ix_bookings_status ON bookings(status);
            CREATE INDEX IF NOT EXISTS ix_bookings_created ON bookings(created_at);

            CREATE TABLE IF NOT EXISTS documents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                booking_id INTEGER NOT NULL REFERENCES bookings(id) ON DELETE CASCADE,
                file_name TEXT NOT NULL,
                file_path TEXT NOT NULL,
                file_type TEXT,
                size_bytes INTEGER,
                uploaded_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL UNIQUE,
                password_hash TEXT NOT NULL,
                role TEXT NOT NULL DEFAULT 'owner',
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS shop_config (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                shop_name TEXT NOT NULL DEFAULT 'Click2Serve',
                owner_name TEXT NOT NULL DEFAULT '',
                owner_phone TEXT NOT NULL DEFAULT '',
                address TEXT NOT NULL DEFAULT '',
                upi_vpa TEXT NOT NULL DEFAULT '',
                upi_payee_name TEXT NOT NULL DEFAULT '',
                opening_hours TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            );
            """
        )

        # Idempotent migrations — keep already-deployed databases compatible.
        _add_column_if_missing(conn, "bookings", "payment_status",
                               "TEXT NOT NULL DEFAULT 'unpaid'")
        _add_column_if_missing(conn, "bookings", "payment_ref", "TEXT")

        # Ensure the singleton shop_config row exists.
        from datetime import datetime as _dt
        conn.execute(
            "INSERT OR IGNORE INTO shop_config (id, updated_at) VALUES (1, ?)",
            (_dt.utcnow().isoformat(timespec="seconds"),),
        )

    # First-run seed data (services + default admin)
    from .seed import seed_services_if_empty, seed_default_admin_if_empty

    seed_services_if_empty()
    seed_default_admin_if_empty()


# ──────────────────────────────────────────────────────────────────────────────
# Services
# ──────────────────────────────────────────────────────────────────────────────
def list_services(active_only: bool = True) -> list[sqlite3.Row]:
    sql = "SELECT * FROM services"
    if active_only:
        sql += " WHERE active = 1"
    sql += " ORDER BY category, name"
    with get_conn() as conn:
        return list(conn.execute(sql))


def get_service(service_id: int) -> sqlite3.Row | None:
    with get_conn() as conn:
        return conn.execute("SELECT * FROM services WHERE id = ?", (service_id,)).fetchone()


def list_categories() -> list[str]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT DISTINCT category FROM services WHERE active = 1 ORDER BY category"
        ).fetchall()
    return [r["category"] for r in rows]


# ──────────────────────────────────────────────────────────────────────────────
# Bookings
# ──────────────────────────────────────────────────────────────────────────────
def _new_token() -> str:
    """Short, customer-friendly token: C2S-XXXX (4 hex chars, ~65k space)."""
    return f"C2S-{secrets.token_hex(2).upper()}"


def create_booking(
    *,
    service_id: int,
    customer_name: str,
    customer_phone: str,
    customer_email: str | None = None,
    notes: str | None = None,
) -> tuple[int, str]:
    """Insert a new booking. Returns (booking_id, token)."""
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        # Loop in the unlikely case of token collision
        for _ in range(5):
            token = _new_token()
            existing = conn.execute(
                "SELECT 1 FROM bookings WHERE token = ?", (token,)
            ).fetchone()
            if not existing:
                break
        else:
            # Fall back to a longer token if 5 retries collide
            token = f"C2S-{secrets.token_hex(4).upper()}"

        cur = conn.execute(
            """
            INSERT INTO bookings (
                token, service_id, customer_name, customer_phone,
                customer_email, notes, status, payment_method,
                amount_paid, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 'Pending', 'Unpaid', 0, ?, ?)
            """,
            (
                token, service_id, customer_name.strip(), customer_phone.strip(),
                (customer_email or "").strip() or None,
                (notes or "").strip() or None, now, now,
            ),
        )
        return cur.lastrowid, token


def get_booking_by_token(token: str, phone: str | None = None) -> sqlite3.Row | None:
    sql = """
        SELECT b.*, s.name AS service_name, s.category AS service_category,
               s.govt_fee, s.service_charge, s.eta_hours
        FROM bookings b
        JOIN services s ON s.id = b.service_id
        WHERE UPPER(b.token) = UPPER(?)
    """
    params: list[Any] = [token.strip()]
    if phone:
        sql += " AND b.customer_phone = ?"
        params.append(phone.strip())
    with get_conn() as conn:
        return conn.execute(sql, params).fetchone()


def list_bookings(
    *,
    status: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
    search: str | None = None,
    limit: int = 500,
) -> list[sqlite3.Row]:
    where: list[str] = []
    params: list[Any] = []
    if status and status != "All":
        where.append("b.status = ?")
        params.append(status)
    if date_from:
        where.append("DATE(b.created_at) >= DATE(?)")
        params.append(date_from.isoformat())
    if date_to:
        where.append("DATE(b.created_at) <= DATE(?)")
        params.append(date_to.isoformat())
    if search:
        where.append(
            "(b.token LIKE ? OR b.customer_name LIKE ? OR b.customer_phone LIKE ?)"
        )
        like = f"%{search.strip()}%"
        params.extend([like, like, like])

    sql = """
        SELECT b.*, s.name AS service_name, s.category AS service_category,
               s.govt_fee + s.service_charge AS total_fee
        FROM bookings b
        JOIN services s ON s.id = b.service_id
    """
    if where:
        sql += " WHERE " + " AND ".join(where)
    sql += " ORDER BY b.created_at DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        return list(conn.execute(sql, params))


def update_booking_status(booking_id: int, status: str) -> None:
    if status not in STATUSES:
        raise ValueError(f"Invalid status: {status}")
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            "UPDATE bookings SET status = ?, updated_at = ? WHERE id = ?",
            (status, now, booking_id),
        )


def update_booking_payment(
    booking_id: int, *, method: str, amount: int
) -> None:
    if method not in PAYMENT_METHODS:
        raise ValueError(f"Invalid payment method: {method}")
    # Owner-marked payments (Cash/Card/UPI) are inherently verified;
    # the only "submitted" path is when a customer pastes a UTR online.
    payment_status = "unpaid" if method == "Unpaid" else "verified"
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE bookings
               SET payment_method = ?,
                   amount_paid = ?,
                   payment_status = ?,
                   updated_at = ?
             WHERE id = ?
            """,
            (method, int(amount), payment_status, now, booking_id),
        )


# ──────────────────────────────────────────────────────────────────────────────
# Documents
# ──────────────────────────────────────────────────────────────────────────────
def save_document(
    booking_id: int, *, file_name: str, file_bytes: bytes, file_type: str | None
) -> str:
    """Save uploaded bytes to ./uploads/<booking_id>/<filename> and record it."""
    _ensure_dirs()
    booking_dir = UPLOAD_DIR / str(booking_id)
    booking_dir.mkdir(exist_ok=True)
    safe_name = "".join(c for c in file_name if c.isalnum() or c in "._- ").strip() or "file"
    target = booking_dir / safe_name
    # Avoid silent overwrite — append a counter if needed
    counter = 1
    while target.exists():
        stem = target.stem
        suffix = target.suffix
        target = booking_dir / f"{stem}_{counter}{suffix}"
        counter += 1
    target.write_bytes(file_bytes)

    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO documents (booking_id, file_name, file_path, file_type,
                                   size_bytes, uploaded_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (booking_id, target.name, str(target), file_type,
             len(file_bytes), now),
        )
    return str(target)


def list_documents(booking_id: int) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return list(conn.execute(
            "SELECT * FROM documents WHERE booking_id = ? ORDER BY uploaded_at",
            (booking_id,),
        ))


# ──────────────────────────────────────────────────────────────────────────────
# Reports
# ──────────────────────────────────────────────────────────────────────────────
def revenue_summary(date_from: date, date_to: date) -> dict[str, Any]:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total_bookings,
                SUM(amount_paid) AS revenue,
                SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) AS delivered,
                SUM(CASE WHEN status = 'Cancelled' THEN 1 ELSE 0 END) AS cancelled,
                SUM(CASE WHEN payment_method = 'Unpaid' THEN 1 ELSE 0 END) AS unpaid
            FROM bookings
            WHERE DATE(created_at) BETWEEN DATE(?) AND DATE(?)
            """,
            (date_from.isoformat(), date_to.isoformat()),
        ).fetchone()
        return {
            "total_bookings": row["total_bookings"] or 0,
            "revenue": row["revenue"] or 0,
            "delivered": row["delivered"] or 0,
            "cancelled": row["cancelled"] or 0,
            "unpaid": row["unpaid"] or 0,
        }


def revenue_by_day(date_from: date, date_to: date) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return list(conn.execute(
            """
            SELECT DATE(created_at) AS day,
                   COUNT(*) AS bookings,
                   COALESCE(SUM(amount_paid), 0) AS revenue
            FROM bookings
            WHERE DATE(created_at) BETWEEN DATE(?) AND DATE(?)
            GROUP BY DATE(created_at)
            ORDER BY day
            """,
            (date_from.isoformat(), date_to.isoformat()),
        ))


def revenue_by_service(date_from: date, date_to: date) -> list[sqlite3.Row]:
    with get_conn() as conn:
        return list(conn.execute(
            """
            SELECT s.name AS service_name,
                   COUNT(*) AS bookings,
                   COALESCE(SUM(b.amount_paid), 0) AS revenue
            FROM bookings b
            JOIN services s ON s.id = b.service_id
            WHERE DATE(b.created_at) BETWEEN DATE(?) AND DATE(?)
            GROUP BY s.name
            ORDER BY revenue DESC, bookings DESC
            """,
            (date_from.isoformat(), date_to.isoformat()),
        ))


def today_kpis() -> dict[str, Any]:
    today = date.today().isoformat()
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT
                COUNT(*) AS total,
                SUM(CASE WHEN status = 'Pending' THEN 1 ELSE 0 END) AS pending,
                SUM(CASE WHEN status = 'In Progress' THEN 1 ELSE 0 END) AS in_progress,
                SUM(CASE WHEN status = 'Ready' THEN 1 ELSE 0 END) AS ready,
                SUM(CASE WHEN status = 'Delivered' THEN 1 ELSE 0 END) AS delivered,
                COALESCE(SUM(amount_paid), 0) AS revenue
            FROM bookings
            WHERE DATE(created_at) = DATE(?)
            """,
            (today,),
        ).fetchone()
    return {k: row[k] or 0 for k in row.keys()}



# ──────────────────────────────────────────────────────────────────────────────
# Shop config (singleton row)
# ──────────────────────────────────────────────────────────────────────────────
def get_shop_config() -> sqlite3.Row:
    """Return the singleton shop_config row, creating defaults if missing."""
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM shop_config WHERE id = 1").fetchone()
        if row is None:
            now = datetime.utcnow().isoformat(timespec="seconds")
            conn.execute(
                "INSERT INTO shop_config (id, updated_at) VALUES (1, ?)",
                (now,),
            )
            row = conn.execute("SELECT * FROM shop_config WHERE id = 1").fetchone()
        return row


def update_shop_config(**fields: Any) -> None:
    """Update any subset of shop_config columns. Unknown keys are ignored."""
    allowed = {
        "shop_name", "owner_name", "owner_phone", "address",
        "upi_vpa", "upi_payee_name", "opening_hours",
    }
    clean = {k: (v.strip() if isinstance(v, str) else v)
             for k, v in fields.items() if k in allowed}
    if not clean:
        return
    set_clause = ", ".join(f"{k} = ?" for k in clean)
    params = list(clean.values())
    params.append(datetime.utcnow().isoformat(timespec="seconds"))
    with get_conn() as conn:
        conn.execute(
            f"UPDATE shop_config SET {set_clause}, updated_at = ? WHERE id = 1",
            params,
        )


# ──────────────────────────────────────────────────────────────────────────────
# Online-payment lifecycle (UPI flow)
#
#   payment_status transitions:
#     unpaid → submitted          (customer pasted UTR)
#     submitted → verified        (owner saw the credit in their UPI app)
#     submitted → rejected        (UTR doesn't match → reverts to unpaid)
# ──────────────────────────────────────────────────────────────────────────────
def submit_payment_proof(
    booking_id: int, *, ref: str, amount: int, method: str = "UPI"
) -> None:
    """Customer submits a UTR / transaction reference for verification."""
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE bookings
               SET payment_method = ?,
                   payment_status = 'submitted',
                   payment_ref = ?,
                   amount_paid = ?,
                   updated_at = ?
             WHERE id = ?
            """,
            (method, ref.strip(), int(amount), now, booking_id),
        )


def verify_payment(booking_id: int) -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            "UPDATE bookings SET payment_status = 'verified', updated_at = ? "
            "WHERE id = ?",
            (now, booking_id),
        )


def reject_payment(booking_id: int) -> None:
    """Reset the booking to unpaid so the customer can retry."""
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            """
            UPDATE bookings
               SET payment_status = 'rejected',
                   payment_ref = NULL,
                   payment_method = 'Unpaid',
                   amount_paid = 0,
                   updated_at = ?
             WHERE id = ?
            """,
            (now, booking_id),
        )



def pending_verification_count() -> int:
    """Number of bookings where the customer submitted a UTR but the owner
    hasn't verified or rejected it yet. Used as a dashboard badge."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT COUNT(*) AS c FROM bookings WHERE payment_status = 'submitted'"
        ).fetchone()
    return row["c"] or 0
