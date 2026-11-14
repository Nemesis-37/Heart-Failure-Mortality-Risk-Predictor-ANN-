"""
auth/dependencies.py
====================
Reusable FastAPI authentication and authorization dependency for physicians.

Ensures that:
1. A valid, non-expired Bearer access token is supplied in Authorization header.
2. The doctor exists in the database.
3. The doctor's institutional email has been verified via OTP.
4. The doctor's medical council credentials have been APPROVED by hospital administration.
5. The doctor's account is currently active.
"""

from typing import Optional
from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from auth.session_service import verify_access_token
try:
    from db_models import Doctor
except ImportError:
    from database.models import Doctor

try:
    from database import get_db
except ImportError:
    from database.config import get_db


def get_current_doctor(
    authorization: Optional[str] = Header(None, description="Bearer <access_token>"),
    db: Session = Depends(get_db),
) -> Doctor:
    """
    FastAPI dependency to protect physician endpoints.
    Enforces authentication, email verification, administrative approval, and active status.
    """
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Physician authorization required. Please log in to your clinical portal.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = authorization.split("Bearer ", 1)[1].strip()
    payload = verify_access_token(token)

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session token. Please log in again.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    doctor_id = payload.get("sub")
    if not doctor_id:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Malformed session token. Access denied.",
        )

    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Physician account not found.",
        )

    # 1. Enforce active account status
    if not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your physician account has been deactivated or suspended. Please contact hospital administration.",
        )

    # 2. Enforce email verification
    if not doctor.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your professional email address has not been verified. Complete 6-digit OTP verification to proceed.",
        )

    # 3. Enforce administrative credential approval
    if doctor.verification_status != "APPROVED":
        if doctor.verification_status == "REJECTED":
            reason = doctor.rejection_reason or "Medical council registration could not be verified."
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Your physician registration was rejected: {reason}",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access denied. Your medical credentials are pending administrator review and approval.",
            )

    return doctor
