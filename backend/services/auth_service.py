"""Access requests, one-time passwords and session tokens."""

import hashlib
import hmac
import logging
import secrets
import time
from datetime import datetime, timedelta, timezone
from typing import Literal

import jwt

from config import settings
from services import email_service
from services.db import get_conn

logger = logging.getLogger("knowly.auth")

UserStatus = Literal["pending", "approved", "rejected"]


class InvalidOTPError(Exception):
    pass


def normalize_email(email: str) -> str:
    return email.strip().lower()


def is_admin(email: str) -> bool:
    return normalize_email(email) in settings.admin_emails


def ensure_admins_approved() -> None:
    """Admins configured via ADMIN_EMAILS always exist as approved users."""
    now = time.time()
    with get_conn() as conn:
        for email in settings.admin_emails:
            conn.execute(
                """
                INSERT INTO users (email, status, created_at, decided_at) VALUES (?, 'approved', ?, ?)
                ON CONFLICT(email) DO UPDATE SET status = 'approved'
                """,
                (email, now, now),
            )


def get_user(email: str) -> dict | None:
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM users WHERE email = ?", (normalize_email(email),)).fetchone()
    return dict(row) if row else None


def list_users(status: UserStatus | None = None) -> list[dict]:
    query = "SELECT * FROM users"
    params: tuple = ()
    if status is not None:
        query += " WHERE status = ?"
        params = (status,)
    query += " ORDER BY created_at DESC"
    with get_conn() as conn:
        return [dict(r) for r in conn.execute(query, params).fetchall()]


def set_user_status(email: str, status: UserStatus) -> dict | None:
    """Change a user's status. Revoking/rejecting also invalidates existing sessions."""
    email = normalize_email(email)
    with get_conn() as conn:
        row = conn.execute("SELECT status FROM users WHERE email = ?", (email,)).fetchone()
        if row is None:
            return None
        previous = row["status"]
        conn.execute(
            """
            UPDATE users
            SET status = ?, decided_at = ?,
                token_version = token_version + CASE WHEN ? != 'approved' THEN 1 ELSE 0 END
            WHERE email = ?
            """,
            (status, time.time(), status, email),
        )
        if status != "approved":
            conn.execute("DELETE FROM otp_codes WHERE email = ?", (email,))

    if status == "approved" and previous != "approved":
        try:
            email_service.send_access_approved_email(email)
        except Exception:
            logger.exception("Could not send approval email to %s", email)

    return get_user(email)


# ---------------------------------------------------------------------------
# Login flow
# ---------------------------------------------------------------------------

def _hash_code(email: str, code: str) -> str:
    return hmac.new(settings.jwt_secret.encode(), f"{email}:{code}".encode(), hashlib.sha256).hexdigest()


def start_login(email: str) -> Literal["otp_sent", "pending"]:
    """Entry point for the login screen.

    - Approved users (and admins) receive a one-time code by email.
    - Unknown emails are registered as a pending access request.
    - Pending/rejected users are told their request is pending.
    """
    email = normalize_email(email)
    now = time.time()

    if is_admin(email):
        ensure_admins_approved()

    user = get_user(email)

    if user is None:
        with get_conn() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO users (email, status, created_at) VALUES (?, 'pending', ?)",
                (email, now),
            )
        try:
            email_service.send_new_request_email(email)
        except Exception:
            logger.exception("Could not notify admins about request from %s", email)
        return "pending"

    if user["status"] != "approved":
        return "pending"

    with get_conn() as conn:
        existing = conn.execute("SELECT sent_at FROM otp_codes WHERE email = ?", (email,)).fetchone()
        if existing and now - existing["sent_at"] < settings.otp_resend_cooldown_seconds:
            # A code was just sent; don't spam the inbox.
            return "otp_sent"

        code = f"{secrets.randbelow(10**6):06d}"
        conn.execute(
            """
            INSERT INTO otp_codes (email, code_hash, expires_at, attempts, sent_at) VALUES (?, ?, ?, 0, ?)
            ON CONFLICT(email) DO UPDATE SET
                code_hash = excluded.code_hash, expires_at = excluded.expires_at,
                attempts = 0, sent_at = excluded.sent_at
            """,
            (email, _hash_code(email, code), now + settings.otp_expire_minutes * 60, now),
        )

    try:
        email_service.send_otp_email(email, code)
    except Exception:
        # Drop the code so the cooldown doesn't block a retry.
        with get_conn() as conn:
            conn.execute("DELETE FROM otp_codes WHERE email = ?", (email,))
        raise
    return "otp_sent"


def verify_otp(email: str, code: str) -> str:
    """Validate a one-time code and return a session token."""
    email = normalize_email(email)
    code = code.strip()

    # Errors are raised after the `with` block so the attempt counter is committed.
    error: str | None = None
    user = None
    with get_conn() as conn:
        row = conn.execute("SELECT * FROM otp_codes WHERE email = ?", (email,)).fetchone()
        if row is None or row["expires_at"] < time.time() or row["attempts"] >= settings.otp_max_attempts:
            error = "El código es inválido o venció. Pedí uno nuevo."
        elif not hmac.compare_digest(row["code_hash"], _hash_code(email, code)):
            conn.execute("UPDATE otp_codes SET attempts = attempts + 1 WHERE email = ?", (email,))
            error = "Código incorrecto."
        else:
            conn.execute("DELETE FROM otp_codes WHERE email = ?", (email,))
            user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()

    if error:
        raise InvalidOTPError(error)
    if user is None or user["status"] != "approved":
        raise InvalidOTPError("Tu acceso no está aprobado.")

    return create_token(email, user["token_version"])


# ---------------------------------------------------------------------------
# Tokens
# ---------------------------------------------------------------------------

def create_token(email: str, token_version: int) -> str:
    payload = {
        "sub": email,
        "tv": token_version,
        "exp": datetime.now(tz=timezone.utc) + timedelta(days=settings.jwt_expire_days),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm="HS256")


def user_from_token(token: str) -> dict | None:
    """Return the user for a valid token, or None if invalid, expired or revoked."""
    try:
        payload = jwt.decode(token, settings.jwt_secret, algorithms=["HS256"])
    except jwt.InvalidTokenError:
        return None

    user = get_user(payload.get("sub", ""))
    if user is None or user["status"] != "approved" or user["token_version"] != payload.get("tv"):
        return None
    return user
