"""
auth/session_service.py
=======================
Cryptographic access token generation, revocable database refresh sessions,
and rate-limiting protection for physician login.

Security Architecture:
- Short-lived Access Tokens (30 minutes) signed with HMAC-SHA256.
- Revocable Refresh Sessions stored in database (7 days default, 30 days if remember_me).
- Refresh tokens are hashed before storage; raw tokens are never persisted.
- Refresh token rotation upon renewal (mitigates replay attacks).
- Memory-based rate limiting per email (5 attempts / 5-minute lockout).
"""

import base64
import hashlib
import hmac
import json
import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Dict, Optional, Tuple

from dotenv import load_dotenv
from sqlalchemy.orm import Session

from database.models import Doctor, DoctorSession

logger = logging.getLogger(__name__)

# Load secret key from .env
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

SECRET_KEY = os.getenv("JWT_SECRET_KEY", os.getenv("ADMIN_SECRET_KEY", "clinical-saas-doctor-auth-key-2026")).encode("utf-8")

ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7
REMEMBER_ME_REFRESH_DAYS = 30

# In-memory rate limiting tracker: { email: [timestamp1, timestamp2, ...] }
_FAILED_LOGIN_ATTEMPTS: Dict[str, list] = {}
RATE_LIMIT_MAX_ATTEMPTS = 5
RATE_LIMIT_WINDOW_SECONDS = 300  # 5 minutes


# ---------------------------------------------------------------------------
# Rate Limiting Helper
# ---------------------------------------------------------------------------

def check_login_rate_limit(email: str) -> Tuple[bool, int]:
    """
    Check if an email is rate-limited due to repeated failed login attempts.
    Returns (is_allowed, wait_seconds).
    """
    clean_email = email.strip().lower()
    now = time.time()
    attempts = _FAILED_LOGIN_ATTEMPTS.get(clean_email, [])
    # Keep only attempts within the sliding window
    valid_attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW_SECONDS]
    _FAILED_LOGIN_ATTEMPTS[clean_email] = valid_attempts

    if len(valid_attempts) >= RATE_LIMIT_MAX_ATTEMPTS:
        oldest = valid_attempts[0]
        wait_seconds = int(RATE_LIMIT_WINDOW_SECONDS - (now - oldest))
        return False, max(wait_seconds, 1)

    return True, 0


def record_login_failure(email: str) -> int:
    """Record a failed login attempt and return total recent failures."""
    clean_email = email.strip().lower()
    now = time.time()
    attempts = _FAILED_LOGIN_ATTEMPTS.get(clean_email, [])
    valid_attempts = [t for t in attempts if now - t < RATE_LIMIT_WINDOW_SECONDS]
    valid_attempts.append(now)
    _FAILED_LOGIN_ATTEMPTS[clean_email] = valid_attempts
    return len(valid_attempts)


def reset_login_failures(email: str) -> None:
    """Clear failed attempts upon successful login."""
    clean_email = email.strip().lower()
    _FAILED_LOGIN_ATTEMPTS.pop(clean_email, None)


# ---------------------------------------------------------------------------
# Cryptographic Token Helpers (HMAC-SHA256 Signed JSON Web Token)
# ---------------------------------------------------------------------------

def _b64_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode("utf-8").rstrip("=")


def _b64_decode(data: str) -> bytes:
    padding = "=" * (4 - (len(data) % 4)) if len(data) % 4 != 0 else ""
    return base64.urlsafe_b64decode(data + padding)


def create_access_token(
    doctor_id: str,
    email: str,
    full_name: str,
    expires_delta: Optional[timedelta] = None,
) -> str:
    """Create a signed, short-lived access token."""
    now = int(time.time())
    expire = now + int((expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)).total_seconds())

    header = {"alg": "HS256", "typ": "JWT"}
    payload = {
        "sub": doctor_id,
        "email": email,
        "name": full_name,
        "role": "doctor",
        "type": "access",
        "iat": now,
        "exp": expire,
    }

    header_b64 = _b64_encode(json.dumps(header).encode("utf-8"))
    payload_b64 = _b64_encode(json.dumps(payload).encode("utf-8"))
    message = f"{header_b64}.{payload_b64}"
    signature = hmac.new(SECRET_KEY, message.encode("utf-8"), hashlib.sha256).digest()
    sig_b64 = _b64_encode(signature)

    return f"{message}.{sig_b64}"


def verify_access_token(token: str) -> Optional[dict]:
    """Verify access token signature and expiration. Returns payload dict if valid."""
    if not token or token.count(".") != 2:
        return None

    try:
        header_b64, payload_b64, sig_b64 = token.split(".")
        message = f"{header_b64}.{payload_b64}"
        expected_sig = hmac.new(SECRET_KEY, message.encode("utf-8"), hashlib.sha256).digest()
        provided_sig = _b64_decode(sig_b64)

        if not hmac.compare_digest(expected_sig, provided_sig):
            return None

        payload = json.loads(_b64_decode(payload_b64).decode("utf-8"))
        now = int(time.time())

        # Check expiration
        if payload.get("exp", 0) < now:
            return None

        # Check token type
        if payload.get("type") != "access":
            return None

        return payload
    except Exception as exc:
        logger.debug(f"Access token verification failed: {exc}")
        return None


# ---------------------------------------------------------------------------
# Database Refresh Session Management
# ---------------------------------------------------------------------------

def _hash_refresh_token(raw_token: str) -> str:
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def create_doctor_session(
    db: Session,
    doctor: Doctor,
    remember_me: bool = False,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> Tuple[str, str, int]:
    """
    Create a persistent, revocable refresh session in database.
    Returns (access_token, raw_refresh_token, expires_in_seconds).
    """
    access_token = create_access_token(doctor.doctor_id, doctor.email, doctor.full_name)

    raw_refresh_token = secrets.token_urlsafe(48)
    refresh_hash = _hash_refresh_token(raw_refresh_token)

    days = REMEMBER_ME_REFRESH_DAYS if remember_me else REFRESH_TOKEN_EXPIRE_DAYS
    expires_at = datetime.now(timezone.utc) + timedelta(days=days)

    session = DoctorSession(
        session_id=str(secrets.token_hex(16)),
        doctor_id=doctor.doctor_id,
        refresh_token_hash=refresh_hash,
        expires_at=expires_at,
        is_revoked=False,
        created_at=datetime.now(timezone.utc),
        user_agent=user_agent[:256] if user_agent else None,
        ip_address=ip_address[:64] if ip_address else None,
    )
    db.add(session)
    db.commit()

    return access_token, raw_refresh_token, ACCESS_TOKEN_EXPIRE_MINUTES * 60


def rotate_refresh_token(
    db: Session,
    raw_refresh_token: str,
    user_agent: Optional[str] = None,
    ip_address: Optional[str] = None,
) -> Optional[Tuple[str, str, Doctor]]:
    """
    Verify and rotate a refresh token.
    Enforces that doctor is still active and approved.
    Returns (new_access_token, new_refresh_token, doctor) or None.
    """
    refresh_hash = _hash_refresh_token(raw_refresh_token.strip())
    session = (
        db.query(DoctorSession)
        .filter(DoctorSession.refresh_token_hash == refresh_hash)
        .first()
    )

    if not session or session.is_revoked:
        return None

    expires_at = session.expires_at
    if expires_at and expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)

    if expires_at and datetime.now(timezone.utc) > expires_at:
        session.is_revoked = True
        db.commit()
        return None

    # Fetch doctor and verify active credentials
    doctor = db.query(Doctor).filter(Doctor.doctor_id == session.doctor_id).first()
    if not doctor or not doctor.is_active or doctor.verification_status != "APPROVED":
        session.is_revoked = True
        db.commit()
        return None

    # Revoke old session and issue new session (Token Rotation)
    session.is_revoked = True

    new_access_token = create_access_token(doctor.doctor_id, doctor.email, doctor.full_name)
    new_raw_refresh = secrets.token_urlsafe(48)
    new_hash = _hash_refresh_token(new_raw_refresh)

    new_session = DoctorSession(
        session_id=str(secrets.token_hex(16)),
        doctor_id=doctor.doctor_id,
        refresh_token_hash=new_hash,
        expires_at=datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
        is_revoked=False,
        created_at=datetime.now(timezone.utc),
        user_agent=user_agent[:256] if user_agent else None,
        ip_address=ip_address[:64] if ip_address else None,
    )
    db.add(new_session)
    db.commit()

    return new_access_token, new_raw_refresh, doctor


def revoke_doctor_session(db: Session, raw_refresh_token: str) -> bool:
    """Revoke a refresh session upon logout."""
    if not raw_refresh_token:
        return False
    refresh_hash = _hash_refresh_token(raw_refresh_token.strip())
    session = (
        db.query(DoctorSession)
        .filter(DoctorSession.refresh_token_hash == refresh_hash)
        .first()
    )
    if session:
        session.is_revoked = True
        db.commit()
        return True
    return False
