"""Owner authentication using SHA-256 password hashing.

For an MVP this is sufficient: there is one shop owner per deployment, the DB
file is local, and the cost of compromise is bounded. For multi-staff or
public hosting, swap in `bcrypt` or `argon2-cffi`.
"""
from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime

from .db import get_conn

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "click2serve123"  # change after first login


def _hash_password(password: str, salt: str) -> str:
    """Salted SHA-256 — `salt$hash` so we can verify later."""
    digest = hashlib.sha256(f"{salt}{password}".encode("utf-8")).hexdigest()
    return f"{salt}${digest}"


def hash_password(password: str) -> str:
    return _hash_password(password, secrets.token_hex(8))


def verify_password(password: str, stored: str) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, _ = stored.split("$", 1)
    expected = _hash_password(password, salt)
    return hmac.compare_digest(expected, stored)


def authenticate(username: str, password: str) -> bool:
    """Return True if the credentials match an existing user."""
    with get_conn() as conn:
        row = conn.execute(
            "SELECT password_hash FROM users WHERE username = ?",
            (username.strip().lower(),),
        ).fetchone()
    if not row:
        return False
    return verify_password(password, row["password_hash"])


def change_password(username: str, new_password: str) -> bool:
    with get_conn() as conn:
        cur = conn.execute(
            "UPDATE users SET password_hash = ? WHERE username = ?",
            (hash_password(new_password), username.strip().lower()),
        )
        return cur.rowcount > 0


def create_user(username: str, password: str, role: str = "owner") -> None:
    now = datetime.utcnow().isoformat(timespec="seconds")
    with get_conn() as conn:
        conn.execute(
            "INSERT INTO users (username, password_hash, role, created_at) "
            "VALUES (?, ?, ?, ?)",
            (username.strip().lower(), hash_password(password), role, now),
        )
