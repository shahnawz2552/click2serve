"""Owner authentication using bcrypt.

bcrypt is a slow, salt-baked, intentionally-expensive password hash.
It is the right default for password storage today: each call to
``hashpw`` generates a fresh salt and runs the work-factor-tunable
Blowfish-derived key schedule, so a stolen DB does not let an attacker
mount fast offline brute-force attacks.

Backwards compatibility: stored hashes that begin with ``$2`` are bcrypt;
anything else is treated as legacy and rejected. The default admin user
is reseeded with a bcrypt hash on first run.
"""
from __future__ import annotations

from datetime import datetime, timezone

import bcrypt

from .db import get_supabase

DEFAULT_ADMIN_USERNAME = "admin"
DEFAULT_ADMIN_PASSWORD = "click2serve123"  # change after first login

# Work factor — 12 is the modern default. Higher = slower = more secure
# but also slower for legitimate users. 12 ≈ ~250 ms on a typical CPU.
_BCRYPT_ROUNDS = 12


def hash_password(password: str) -> str:
    """Return a fresh bcrypt hash for ``password`` (UTF-8 safe)."""
    salt = bcrypt.gensalt(rounds=_BCRYPT_ROUNDS)
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")


def verify_password(password: str, stored: str) -> bool:
    """Constant-time check against a stored bcrypt hash."""
    if not stored or not stored.startswith("$2"):
        return False
    try:
        return bcrypt.checkpw(password.encode("utf-8"), stored.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def authenticate(username: str, password: str) -> bool:
    """Return True if the credentials match an existing user row."""
    sb = get_supabase()
    res = (
        sb.table("users")
        .select("password_hash")
        .eq("username", username.strip().lower())
        .limit(1)
        .execute()
    )
    rows = res.data or []
    if not rows:
        return False
    return verify_password(password, rows[0]["password_hash"])


def change_password(username: str, new_password: str) -> bool:
    sb = get_supabase()
    res = (
        sb.table("users")
        .update({"password_hash": hash_password(new_password)})
        .eq("username", username.strip().lower())
        .execute()
    )
    return bool(res.data)


def create_user(username: str, password: str, role: str = "owner") -> None:
    sb = get_supabase()
    sb.table("users").insert(
        {
            "username": username.strip().lower(),
            "password_hash": hash_password(password),
            "role": role,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
    ).execute()
