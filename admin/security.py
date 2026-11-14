"""
admin/security.py
=================
Administrator authentication, signed session token generation, and role authorization.
"""

import hashlib
import hmac
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
from fastapi import Header, HTTPException, status
from database.models import Administrator

_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)

ADMIN_SECRET_KEY = os.getenv("ADMIN_SECRET_KEY", "clinical-saas-admin-super-secure-key-2026").encode("utf-8")
TOKEN_VALIDITY_SECONDS = 12 * 3600  # 12 hours


def create_admin_token(admin_id: str, username: str) -> str:
    """Create a cryptographically signed admin session token with timestamp."""
    issued_at = int(time.time())
    payload = f"{admin_id}:{username}:{issued_at}"
    signature = hmac.new(ADMIN_SECRET_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"{admin_id}.{issued_at}.{signature}"


def verify_admin_token(token: str) -> Optional[str]:
    """Verify admin token signature and expiration. Returns admin_id if valid."""
    if not token or "." not in token:
        return None
    parts = token.split(".")
    if len(parts) != 3:
        return None

    admin_id, issued_at_str, signature = parts
    try:
        issued_at = int(issued_at_str)
    except ValueError:
        return None

    # Check expiration (12 hours)
    if time.time() - issued_at > TOKEN_VALIDITY_SECONDS:
        return None

    # Verify signature
    # Fetch admin username to verify HMAC
    from database.config import SessionLocal
    db = SessionLocal()
    try:
        admin = db.query(Administrator).filter(Administrator.admin_id == admin_id).first()
        if not admin or not admin.is_active:
            return None

        expected_payload = f"{admin_id}:{admin.username}:{issued_at}"
        expected_sig = hmac.new(ADMIN_SECRET_KEY, expected_payload.encode("utf-8"), hashlib.sha256).hexdigest()
        if hmac.compare_digest(signature, expected_sig):
            return admin_id
        return None
    finally:
        db.close()


def get_current_admin(
    authorization: Optional[str] = Header(None, description="Bearer <admin_token>"),
    x_admin_token: Optional[str] = Header(None, description="Alternative admin header"),
):
    """
    FastAPI dependency to protect administrator routes.
    Ensures only authenticated, active hospital administrators can access credential verification tools.
    """
    raw_token = None
    if isinstance(authorization, str) and authorization.startswith("Bearer "):
        raw_token = authorization.split("Bearer ", 1)[1].strip()
    elif isinstance(x_admin_token, str) and x_admin_token.strip():
        raw_token = x_admin_token.strip()

    if not raw_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Administrator authorization required. Please log in as an administrator.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    admin_id = verify_admin_token(raw_token)
    if not admin_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid or expired administrator session. Access denied.",
        )

    from database.config import SessionLocal
    db = SessionLocal()
    try:
        admin = db.query(Administrator).filter(Administrator.admin_id == admin_id).first()
        if not admin or not admin.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Administrator account is inactive or disabled.",
            )
        return admin
    finally:
        db.close()
