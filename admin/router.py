"""
admin/router.py
===============
FastAPI router for Hospital Administrator:
- Administrator Login & JWT Authentication
- Administrator Password Recovery via 6-digit OTP
- Doctor Credential Verification (Approve / Reject)
- Doctor Management (List, Detail, Toggle Active)
- Doctor Activity Tracking (Derived from DoctorSessions, Assessments, Predictions)
- High-level Clinical System Overview Metrics

Security:
- All management endpoints are strictly gated by `get_current_admin`.
- Medical evidence documents are streamed securely with session authorization;
  files are never exposed in publicly reachable static URLs.
- Doctors cannot approve themselves.
"""

import os
import re
import secrets
import time
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy import func
from sqlalchemy.orm import Session

from admin.schemas import (
    ActionResponse,
    AdminForgotPasswordRequest,
    AdminForgotPasswordResponse,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminOverviewResponse,
    AdminProfile,
    AdminResetPasswordRequest,
    AdminVerifyResetOTPRequest,
    AdminVerifyResetOTPResponse,
    DoctorActivityView,
    DoctorAdminView,
    DoctorRejectionRequest,
    ModelMetricDetail,
    ModelPerformanceResponse,
    RecentActivitySummary,
    RecentDoctorRegistration,
)
from admin.security import create_admin_token, get_current_admin
from auth.email_service import (
    generate_otp,
    hash_otp,
    send_doctor_approval_email,
    send_doctor_rejection_email,
    send_email_otp,
    verify_otp_hash,
)
from auth.security import (
    hash_password,
    is_argon2_native,
    verify_legacy_password,
    verify_password,
)
try:
    from models.metrics import VERIFIED_ANN_METRICS, VERIFIED_LR_METRICS
except ImportError:
    from frontend_metrics import VERIFIED_ANN_METRICS, VERIFIED_LR_METRICS

try:
    from database import get_db
except ImportError:
    from database.config import get_db

try:
    from database.models import Administrator, Assessment, Doctor, DoctorSession, Prediction
except ImportError:
    from db_models import Assessment, Doctor, EmailOTP
    from database.models import Administrator, DoctorSession
    Prediction = None

router = APIRouter(prefix="/admin", tags=["Administrator Portal"])
BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# In-memory store for Admin Password Reset via OTP
# Structure: { username_lower: { otp_hash, expires_at, attempts, last_sent, is_verified, reset_token } }
# ---------------------------------------------------------------------------
_ADMIN_PASSWORD_RESET = {}
ADMIN_RESET_EXPIRY_MINUTES = 5
ADMIN_RESET_MAX_ATTEMPTS = 5
ADMIN_RESET_COOLDOWN_SECONDS = 60
def ensure_initial_admin(db: Session):
    """Seed initial administrator from environment variables if no admin exists."""
    admin_count = db.query(Administrator).count()
    if admin_count == 0:
        env_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
        env_username = os.getenv("ADMIN_USERNAME", "").strip()
        env_password = os.getenv("ADMIN_PASSWORD", "")
        if not env_email or not env_password:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="No administrator account is configured. Set ADMIN_EMAIL and ADMIN_PASSWORD to initialize one.",
            )
        if not env_username:
            env_username = env_email.split("@", 1)[0]
        if not is_argon2_native():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Native Argon2id support is required to initialize an administrator account.",
            )
        new_admin = Administrator(
            admin_id=str(uuid.uuid4()),
            username=env_username,
            email=env_email,
            password_hash=hash_password(env_password),
            full_name="Hospital Administrator",
            role="Super Administrator",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_admin)
        db.commit()


def _generate_unique_username(db: Session, full_name: str, reg_number: str) -> str:
    """Generate a clean, professional, unique username for an approved physician."""
    clean = re.sub(r"[^a-zA-Z0-9]", "", full_name.lower().replace("dr.", "").replace("dr ", "").replace("dr", "").strip())
    if not clean:
        clean = "doctor"
    clean_reg = re.sub(r"[^a-zA-Z0-9]", "", reg_number.lower())[-4:]
    if not clean_reg:
        clean_reg = secrets.token_hex(2)
    candidate_base = f"dr_{clean[:10]}_{clean_reg}"
    candidate = candidate_base
    idx = 1
    while db.query(Doctor).filter(Doctor.username == candidate).first():
        candidate = f"{candidate_base}_{idx}"
        idx += 1
    return candidate


# ---------------------------------------------------------------------------
# 1. Administrator Authentication Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=AdminLoginResponse,
    summary="Hospital Administrator Login",
)
def admin_login(payload: AdminLoginRequest, db: Session = Depends(get_db)):
    """Authenticate administrator credentials and return an authorized session token."""
    username_clean = payload.username.strip()
    admin = db.query(Administrator).filter(
        (Administrator.username == username_clean) | (Administrator.email == username_clean)
    ).first()

    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials or account disabled.",
        )

    if admin.password_hash.startswith("$argon2id-fallback$"):
        password_matches = verify_legacy_password(payload.password, admin.password_hash)
        if password_matches:
            admin.password_hash = hash_password(payload.password)
            db.commit()
    else:
        password_matches = verify_password(payload.password, admin.password_hash)

    if not password_matches:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials.",
        )

    token = create_admin_token(admin.admin_id, admin.username)
    return AdminLoginResponse(
        status="success",
        token=token,
        admin=AdminProfile(
            admin_id=admin.admin_id,
            username=admin.username,
            email=admin.email,
            full_name=admin.full_name,
            role=admin.role,
        ),
    )


@router.get(
    "/me",
    response_model=AdminProfile,
    summary="Get authenticated administrator profile",
)
def get_admin_me(current_admin: Administrator = Depends(get_current_admin)):
    """Return the profile of the currently signed-in administrator."""
    return AdminProfile(
        admin_id=current_admin.admin_id,
        username=current_admin.username,
        email=current_admin.email,
        full_name=current_admin.full_name,
        role=current_admin.role,
    )


# ---------------------------------------------------------------------------
# 2. Administrator Password Recovery Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/forgot-password",
    response_model=AdminForgotPasswordResponse,
    summary="Initiate administrator password recovery via OTP",
)
def admin_forgot_password(
    payload: AdminForgotPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Generate and dispatch a 6-digit OTP to the configured administrator recovery email.
    Enforces a 60-second cooldown between requests.
    """
    if payload.email:
        admin = db.query(Administrator).filter(func.lower(Administrator.email) == payload.email.strip().lower()).first()
    else:
        admin = db.query(Administrator).filter(func.lower(Administrator.username) == payload.username.strip().lower()).first()
    if not admin:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Administrator account with this email does not exist.",
        )
    username_clean = admin.username.strip()

    # Enforce 60-second cooldown
    now_ts = time.time()
    existing_entry = _ADMIN_PASSWORD_RESET.get(username_clean.lower())
    if existing_entry:
        elapsed = now_ts - existing_entry.get("last_sent", 0)
        if elapsed < ADMIN_RESET_COOLDOWN_SECONDS:
            wait_sec = int(ADMIN_RESET_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {wait_sec} seconds before requesting a new verification code.",
            )

    recovery_email = os.getenv("ADMIN_RECOVERY_EMAIL", os.getenv("ADMIN_EMAIL", admin.email)).strip()
    otp_code = generate_otp()
    otp_hash_val = hash_otp(otp_code)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=ADMIN_RESET_EXPIRY_MINUTES)

    _ADMIN_PASSWORD_RESET[username_clean.lower()] = {
        "otp_hash": otp_hash_val,
        "expires_at": expires_at,
        "attempts": 0,
        "last_sent": now_ts,
        "is_verified": False,
        "reset_token": None,
    }

    send_email_otp(
        recipient_email=recovery_email,
        recipient_name=admin.full_name or "Administrator",
        otp_code=otp_code,
    )

    parts = recovery_email.split("@")
    name_part = parts[0]
    domain_part = parts[1] if len(parts) > 1 else ""
    if len(name_part) > 2:
        masked = f"{name_part[0]}***{name_part[-1]}@{domain_part}"
    else:
        masked = f"{name_part[0]}***@{domain_part}"

    return AdminForgotPasswordResponse(
        status="success",
        message="A 6-digit verification code has been dispatched to the configured recovery email.",
        recovery_email_masked=masked,
    )


@router.post(
    "/verify-reset-otp",
    response_model=AdminVerifyResetOTPResponse,
    summary="Verify the administrator password reset OTP",
)
def admin_verify_reset_otp(
    payload: AdminVerifyResetOTPRequest,
    db: Session = Depends(get_db),
):
    """
    Verify the 6-digit recovery OTP.
    Enforces 5-minute expiry and max 5 attempts.
    Returns a cryptographically secure single-use reset token upon success.
    """
    admin_query = db.query(Administrator)
    if payload.email:
        admin_query = admin_query.filter(func.lower(Administrator.email) == payload.email.strip().lower())
    else:
        admin_query = admin_query.filter(func.lower(Administrator.username) == payload.username.strip().lower())
    admin = admin_query.first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator account not found.")
    username_clean = admin.username.strip().lower()
    entry = _ADMIN_PASSWORD_RESET.get(username_clean)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No password reset request found or request expired. Please request a new OTP.",
        )

    # Check expiration
    if datetime.now(timezone.utc) > entry["expires_at"]:
        _ADMIN_PASSWORD_RESET.pop(username_clean, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired (5-minute limit). Please request a new code.",
        )

    # Check attempts
    if entry["attempts"] >= ADMIN_RESET_MAX_ATTEMPTS:
        _ADMIN_PASSWORD_RESET.pop(username_clean, None)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum verification attempts exceeded. Please request a new verification code.",
        )

    entry["attempts"] += 1

    if not verify_otp_hash(payload.otp, entry["otp_hash"]):
        remaining = ADMIN_RESET_MAX_ATTEMPTS - entry["attempts"]
        if remaining <= 0:
            _ADMIN_PASSWORD_RESET.pop(username_clean, None)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect verification code. Maximum attempts reached. Please request a new code.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect verification code. {remaining} attempt(s) remaining.",
        )

    # Valid OTP -> issue single-use reset token
    reset_token = secrets.token_urlsafe(32)
    entry["is_verified"] = True
    entry["reset_token"] = reset_token

    return AdminVerifyResetOTPResponse(
        status="verified",
        message="Verification code validated successfully. You may now set a new administrator password.",
        reset_token=reset_token,
    )


@router.post(
    "/reset-password",
    summary="Set a new password for the administrator",
)
def admin_reset_password(
    payload: AdminResetPasswordRequest,
    db: Session = Depends(get_db),
):
    """
    Set a new password for administrator using either verified reset token or OTP.
    Hashes new password with Argon2id (PBKDF2 fallback) and invalidates the reset session.
    """
    if payload.new_password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password and confirm password do not match.",
        )

    if len(payload.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )
    if not is_argon2_native():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Native Argon2id support is required to reset administrator passwords.",
        )

    admin_query = db.query(Administrator)
    if payload.email:
        admin_query = admin_query.filter(func.lower(Administrator.email) == payload.email.strip().lower())
    else:
        admin_query = admin_query.filter(func.lower(Administrator.username) == payload.username.strip().lower())
    admin = admin_query.first()
    if not admin:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Administrator not found.")
    username_clean = admin.username.strip().lower()
    entry = _ADMIN_PASSWORD_RESET.get(username_clean)
    if not entry:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password reset session expired or invalid. Please start the recovery process again.",
        )

    # Verify authorization
    is_authorized = False
    if payload.reset_token and entry.get("reset_token") == payload.reset_token and entry.get("is_verified"):
        is_authorized = True
    elif payload.otp and verify_otp_hash(payload.otp, entry["otp_hash"]):
        if datetime.now(timezone.utc) <= entry["expires_at"]:
            is_authorized = True

    if not is_authorized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset credentials.",
        )

    # Hash new password
    admin.password_hash = hash_password(payload.new_password)
    db.commit()

    # Invalidate OTP & reset state
    _ADMIN_PASSWORD_RESET.pop(username_clean, None)

    return {
        "status": "success",
        "message": "Administrator password has been reset successfully. You can now sign in with your new password.",
    }


# ---------------------------------------------------------------------------
# 3. Admin Overview & System Metrics
# ---------------------------------------------------------------------------

@router.get(
    "/overview",
    response_model=AdminOverviewResponse,
    summary="Get high-level administrator overview metrics",
)
@router.get(
    "/dashboard/summary",
    response_model=AdminOverviewResponse,
    summary="Get high-level administrator overview metrics (Alias)",
)
def get_admin_overview(
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Aggregated statistics across all doctors, assessments, and predictions."""
    total_docs = db.query(Doctor).count()
    pending_docs = db.query(Doctor).filter(Doctor.verification_status == "PENDING").count()
    approved_docs = db.query(Doctor).filter(Doctor.verification_status == "APPROVED").count()
    rejected_docs = db.query(Doctor).filter(Doctor.verification_status == "REJECTED").count()
    total_asms = db.query(Assessment).count()

    total_preds = 0
    if Prediction is not None:
        try:
            total_preds = db.query(Prediction).count()
        except Exception:
            pass
    if total_preds == 0:
        total_preds = db.query(Assessment).filter(Assessment.predicted_class != None).count()

    db_dialect = "PostgreSQL"
    try:
        from database import engine
        if engine and engine.dialect.name == "sqlite":
            db_dialect = "SQLite"
        elif engine and engine.dialect.name == "postgresql":
            db_dialect = "PostgreSQL"
    except Exception:
        pass

    return AdminOverviewResponse(
        total_doctors=total_docs,
        pending_doctors=pending_docs,
        approved_doctors=approved_docs,
        rejected_doctors=rejected_docs,
        total_assessments=total_asms,
        total_predictions=total_preds,
        database_engine=db_dialect,
    )


@router.get(
    "/dashboard/recent-activity",
    response_model=RecentActivitySummary,
    summary="Recent doctor registrations, activity, and verifications",
)
def get_recent_activity(
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Returns actual recent platform events from the database:
    - Latest 5 registered doctors
    - Recently logged-in doctors
    - Recent doctor credential verifications (approved/rejected)
    - Total assessments & predictions performed in the last 7 days
    """
    # 1. Recent registrations (latest 5)
    recent_regs = (
        db.query(Doctor)
        .order_by(Doctor.created_at.desc())
        .limit(5)
        .all()
    )
    reg_views = [
        RecentDoctorRegistration(
            doctor_id=d.doctor_id,
            full_name=d.full_name,
            username=getattr(d, "username", None),
            email=d.email,
            created_at=d.created_at,
            verification_status=d.verification_status,
        )
        for d in recent_regs
    ]

    # 2. Recently logged-in doctors (derived from last_login or DoctorSessions)
    recent_logins = (
        db.query(Doctor)
        .filter(Doctor.last_login != None)
        .order_by(Doctor.last_login.desc())
        .limit(5)
        .all()
    )
    if not recent_logins:
        recent_logins = db.query(Doctor).order_by(Doctor.created_at.desc()).limit(5).all()

    login_views = []
    for doc in recent_logins:
        last_session = (
            db.query(func.max(DoctorSession.created_at))
            .filter(DoctorSession.doctor_id == doc.doctor_id)
            .scalar()
        )
        last_login_ts = getattr(doc, "last_login", None) or last_session
        asm_count = db.query(Assessment).filter(Assessment.doctor_id == doc.doctor_id).count()
        pred_count = db.query(Assessment).filter(Assessment.doctor_id == doc.doctor_id, Assessment.predicted_class != None).count()
        login_views.append(
            DoctorActivityView(
                doctor_id=doc.doctor_id,
                full_name=doc.full_name,
                username=getattr(doc, "username", None),
                email=doc.email,
                medical_degree=doc.medical_degree,
                registration_number=doc.registration_number,
                verification_status=doc.verification_status,
                is_active=doc.is_active,
                last_login=last_login_ts,
                total_assessments=asm_count,
                total_predictions=pred_count,
            )
        )

    # 3. Recent approvals or rejections (latest 5)
    recent_verifs = (
        db.query(Doctor)
        .filter(Doctor.verified_at != None)
        .order_by(Doctor.verified_at.desc())
        .limit(5)
        .all()
    )
    verif_views = []
    for doc in recent_verifs:
        asm_count = db.query(Assessment).filter(Assessment.doctor_id == doc.doctor_id).count()
        pred_count = db.query(Assessment).filter(Assessment.doctor_id == doc.doctor_id, Assessment.predicted_class != None).count()
        verif_views.append(
            DoctorAdminView(
                doctor_id=doc.doctor_id,
                full_name=doc.full_name,
                username=getattr(doc, "username", None),
                email=doc.email,
                mobile=doc.mobile,
                medical_degree=doc.medical_degree,
                registration_number=doc.registration_number,
                registration_council=doc.registration_council,
                email_verified=doc.email_verified,
                verification_status=doc.verification_status,
                is_active=doc.is_active,
                created_at=doc.created_at,
                last_login=getattr(doc, "last_login", None),
                has_document=bool(doc.document_path and (BASE_DIR / doc.document_path).exists()),
                document_filename=doc.document_filename,
                document_uploaded_at=doc.document_uploaded_at,
                verified_at=doc.verified_at,
                approved_at=getattr(doc, "approved_at", None),
                verified_by=doc.verified_by,
                rejection_reason=doc.rejection_reason,
                total_assessments=asm_count,
                total_predictions=pred_count,
            )
        )

    # 4. Weekly throughput (assessments and predictions performed in last 7 days)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    seven_days_naive = datetime.utcnow() - timedelta(days=7)
    try:
        recent_asms = db.query(Assessment).filter(Assessment.created_at >= seven_days_ago).count()
    except Exception:
        recent_asms = db.query(Assessment).filter(Assessment.created_at >= seven_days_naive).count()

    try:
        recent_preds = db.query(Assessment).filter(
            Assessment.created_at >= seven_days_ago,
            Assessment.predicted_class != None,
        ).count()
    except Exception:
        recent_preds = db.query(Assessment).filter(
            Assessment.created_at >= seven_days_naive,
            Assessment.predicted_class != None,
        ).count()

    return RecentActivitySummary(
        recently_logged_in=login_views,
        recent_verifications=verif_views,
        total_assessments_last_7_days=recent_asms,
        total_predictions_last_7_days=recent_preds,
        recent_registrations=reg_views,
    )


# ---------------------------------------------------------------------------
# 4. Doctor Activity Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/doctor-activity",
    response_model=List[DoctorActivityView],
    summary="Doctor Activity Overview (last login, total assessments, total predictions)",
)
def get_doctor_activity(
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Shows doctor activity derived strictly from existing tables:
    - Last login timestamp from Doctor record or DoctorSessions
    - Total assessments
    - Total predictions
    No online/offline status, heartbeat, or live tracking.
    """
    doctors = db.query(Doctor).order_by(Doctor.full_name.asc()).all()
    results = []
    for doc in doctors:
        last_session = (
            db.query(func.max(DoctorSession.created_at))
            .filter(DoctorSession.doctor_id == doc.doctor_id)
            .scalar()
        )
        last_login_ts = getattr(doc, "last_login", None) or last_session

        asm_count = db.query(Assessment).filter(Assessment.doctor_id == doc.doctor_id).count()

        pred_count = 0
        if Prediction is not None:
            try:
                pred_count = (
                    db.query(Prediction)
                    .join(Assessment, Prediction.assessment_id == (getattr(Assessment, "id", getattr(Assessment, "assessment_id", None))))
                    .filter(Assessment.doctor_id == doc.doctor_id)
                    .count()
                )
            except Exception:
                pass
        if pred_count == 0:
            pred_count = (
                db.query(Assessment)
                .filter(Assessment.doctor_id == doc.doctor_id, Assessment.predicted_class != None)
                .count()
            )

        results.append(
            DoctorActivityView(
                doctor_id=doc.doctor_id,
                full_name=doc.full_name,
                username=getattr(doc, "username", None),
                email=doc.email,
                medical_degree=doc.medical_degree,
                registration_number=doc.registration_number,
                verification_status=doc.verification_status,
                is_active=doc.is_active,
                last_login=last_login_ts,
                total_assessments=asm_count,
                total_predictions=pred_count,
            )
        )
    return results


@router.get(
    "/doctors/{doctor_id}/activity",
    response_model=DoctorActivityView,
    summary="Get single doctor activity metrics (Admin Only)",
)
def get_single_doctor_activity(
    doctor_id: str,
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve activity stats for an individual doctor."""
    doc = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found.",
        )

    last_session = (
        db.query(func.max(DoctorSession.created_at))
        .filter(DoctorSession.doctor_id == doc.doctor_id)
        .scalar()
    )
    last_login_ts = getattr(doc, "last_login", None) or last_session
    asm_count = db.query(Assessment).filter(Assessment.doctor_id == doc.doctor_id).count()
    pred_count = db.query(Assessment).filter(Assessment.doctor_id == doc.doctor_id, Assessment.predicted_class != None).count()

    return DoctorActivityView(
        doctor_id=doc.doctor_id,
        full_name=doc.full_name,
        username=getattr(doc, "username", None),
        email=doc.email,
        medical_degree=doc.medical_degree,
        registration_number=doc.registration_number,
        verification_status=doc.verification_status,
        is_active=doc.is_active,
        last_login=last_login_ts,
        total_assessments=asm_count,
        total_predictions=pred_count,
    )


# ---------------------------------------------------------------------------
# 5. Model Performance Metrics Endpoint
# ---------------------------------------------------------------------------

@router.get(
    "/model-performance",
    response_model=ModelPerformanceResponse,
    summary="Verified 10-Fold Cross-Validation Metrics for LR & ANN (Admin Only)",
)
def get_model_performance(
    current_admin: Administrator = Depends(get_current_admin),
):
    """
    Returns verified retrospective 10-fold stratified cross-validation
    benchmark metrics for both Logistic Regression and ANN models.
    """
    return ModelPerformanceResponse(
        logistic_regression=ModelMetricDetail(**VERIFIED_LR_METRICS),
        artificial_neural_network=ModelMetricDetail(**VERIFIED_ANN_METRICS),
    )


# ---------------------------------------------------------------------------
# 6. Doctor Management & Verification Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/doctors",
    response_model=List[DoctorAdminView],
    summary="List doctors with search, status filtering, and pagination (Admin Only)",
)
def list_doctors(
    status_filter: Optional[str] = Query(None, description="Filter: PENDING, APPROVED, REJECTED, or ALL"),
    search: Optional[str] = Query(None, description="Search by name, email, registration number, or username"),
    skip: int = 0,
    limit: int = 100,
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    List all doctors for clinical credential review and management.
    Supports filtering by status, searching across fields, and pagination.
    """
    if not isinstance(status_filter, str):
        status_filter = None
    if not isinstance(search, str):
        search = None
    if not isinstance(skip, int):
        skip = 0
    if not isinstance(limit, int):
        limit = 100

    query = db.query(Doctor)

    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(Doctor.verification_status == status_filter.upper())

    if search and search.strip():
        term = f"%{search.strip().lower()}%"
        query = query.filter(
            func.lower(Doctor.full_name).like(term)
            | func.lower(Doctor.email).like(term)
            | func.lower(Doctor.registration_number).like(term)
            | func.lower(func.coalesce(Doctor.username, "")).like(term)
        )

    doctors = query.order_by(Doctor.created_at.desc()).offset(skip).limit(limit).all()

    results = []
    for doc in doctors:
        asm_count = db.query(Assessment).filter(Assessment.doctor_id == doc.doctor_id).count()
        pred_count = db.query(Assessment).filter(Assessment.doctor_id == doc.doctor_id, Assessment.predicted_class != None).count()
        results.append(
            DoctorAdminView(
                doctor_id=doc.doctor_id,
                full_name=doc.full_name,
                username=getattr(doc, "username", None),
                email=doc.email,
                mobile=doc.mobile,
                medical_degree=doc.medical_degree,
                registration_number=doc.registration_number,
                registration_council=doc.registration_council,
                email_verified=doc.email_verified,
                verification_status=doc.verification_status,
                is_active=doc.is_active,
                created_at=doc.created_at,
                last_login=getattr(doc, "last_login", None),
                has_document=bool(doc.document_path and (BASE_DIR / doc.document_path).exists()),
                document_filename=doc.document_filename,
                document_uploaded_at=doc.document_uploaded_at,
                verified_at=doc.verified_at,
                approved_at=getattr(doc, "approved_at", None),
                verified_by=doc.verified_by,
                rejection_reason=doc.rejection_reason,
                total_assessments=asm_count,
                total_predictions=pred_count,
            )
        )
    return results


@router.get(
    "/doctors/pending",
    response_model=List[DoctorAdminView],
    summary="List pending doctors awaiting verification (Admin Only)",
)
def list_pending_doctors(
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Direct alias for pending doctor verification queue."""
    return list_doctors(status_filter="PENDING", current_admin=current_admin, db=db)


@router.get(
    "/doctors/{doctor_id}",
    response_model=DoctorAdminView,
    summary="Get detailed doctor profile for credential review (Admin Only)",
)
def get_doctor_detail(
    doctor_id: str,
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve full profile and verification audit trail for a single doctor."""
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found.",
        )

    asm_count = db.query(Assessment).filter(Assessment.doctor_id == doctor.doctor_id).count()
    pred_count = db.query(Assessment).filter(Assessment.doctor_id == doctor.doctor_id, Assessment.predicted_class != None).count()

    return DoctorAdminView(
        doctor_id=doctor.doctor_id,
        full_name=doctor.full_name,
        username=getattr(doctor, "username", None),
        email=doctor.email,
        mobile=doctor.mobile,
        medical_degree=doctor.medical_degree,
        registration_number=doctor.registration_number,
        registration_council=doctor.registration_council,
        email_verified=doctor.email_verified,
        verification_status=doctor.verification_status,
        is_active=doctor.is_active,
        created_at=doctor.created_at,
        last_login=getattr(doctor, "last_login", None),
        has_document=bool(doctor.document_path and (BASE_DIR / doctor.document_path).exists()),
        document_filename=doctor.document_filename,
        document_uploaded_at=doctor.document_uploaded_at,
        verified_at=doctor.verified_at,
        approved_at=getattr(doctor, "approved_at", None),
        verified_by=doctor.verified_by,
        rejection_reason=doctor.rejection_reason,
        total_assessments=asm_count,
        total_predictions=pred_count,
    )


@router.get(
    "/doctors/{doctor_id}/document",
    summary="Securely view doctor registration evidence document (Admin Only)",
)
def view_doctor_document(
    doctor_id: str,
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Stream uploaded medical registration certificate or license evidence.
    Protected against unauthorized public access.
    """
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor or not doctor.document_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No document attached to this doctor record.",
        )

    file_path = BASE_DIR / doctor.document_path
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document file missing from secure vault.",
        )

    media_type = "application/pdf" if file_path.suffix.lower() == ".pdf" else "image/jpeg"
    return FileResponse(
        path=file_path,
        media_type=media_type,
        filename=doctor.document_filename or file_path.name,
    )


@router.patch(
    "/doctors/{doctor_id}/approve",
    response_model=ActionResponse,
    summary="Approve doctor credentials (Admin Only)",
)
@router.post(
    "/doctors/{doctor_id}/approve",
    response_model=ActionResponse,
    summary="Approve doctor credentials (Admin Only)",
)
def approve_doctor(
    doctor_id: str,
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Approve doctor medical credentials.
    Sets verification_status = 'APPROVED'.
    Generates unique system username if not already assigned.
    Records decision timestamp, approved_at, and verifying administrator identity.
    Dispatches formal approval notification email with username.
    Only email-verified doctors can be approved.
    """
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found.",
        )

    if not doctor.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot approve doctor: Email address has not been verified.",
        )

    now = datetime.now(timezone.utc)

    # Assign system username if absent
    if not getattr(doctor, "username", None):
        doctor.username = _generate_unique_username(db, doctor.full_name, doctor.registration_number)

    if doctor.verification_status == "APPROVED":
        return ActionResponse(
            status="already_approved",
            message=f"{doctor.full_name} is already verified and approved.",
            doctor_id=doctor.doctor_id,
            verification_status="APPROVED",
            username=doctor.username,
            verified_at=doctor.verified_at,
            approved_at=getattr(doctor, "approved_at", doctor.verified_at),
        )

    doctor.verification_status = "APPROVED"
    doctor.verified_at = now
    doctor.approved_at = now
    doctor.verified_by = current_admin.admin_id
    doctor.rejection_reason = None
    db.commit()

    # Dispatch approval email
    try:
        send_doctor_approval_email(
            recipient_email=doctor.email,
            recipient_name=doctor.full_name,
            username=doctor.username,
        )
    except Exception:
        pass

    return ActionResponse(
        status="approved",
        message=f"{doctor.full_name} has been approved. System username '{doctor.username}' assigned.",
        doctor_id=doctor.doctor_id,
        verification_status="APPROVED",
        username=doctor.username,
        verified_at=now,
        approved_at=now,
    )


@router.patch(
    "/doctors/{doctor_id}/reject",
    response_model=ActionResponse,
    summary="Reject doctor credentials with recorded reason (Admin Only)",
)
@router.post(
    "/doctors/{doctor_id}/reject",
    response_model=ActionResponse,
    summary="Reject doctor credentials with recorded reason (Admin Only)",
)
def reject_doctor(
    doctor_id: str,
    payload: DoctorRejectionRequest,
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    Reject doctor registration with clinical reason.
    Sets verification_status = 'REJECTED'.
    Records rejection reason, decision timestamp, and verifying administrator identity.
    Dispatches formal rejection email explaining the clinical reason.
    """
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found.",
        )

    now = datetime.now(timezone.utc)
    doctor.verification_status = "REJECTED"
    doctor.verified_at = now
    doctor.verified_by = current_admin.admin_id
    doctor.rejection_reason = payload.reason.strip()
    db.commit()

    # Dispatch rejection email
    try:
        send_doctor_rejection_email(
            recipient_email=doctor.email,
            recipient_name=doctor.full_name,
            rejection_reason=doctor.rejection_reason,
        )
    except Exception:
        pass

    return ActionResponse(
        status="rejected",
        message=f"{doctor.full_name} has been rejected. Reason recorded.",
        doctor_id=doctor.doctor_id,
        verification_status="REJECTED",
        username=getattr(doctor, "username", None),
        verified_at=now,
        rejection_reason=doctor.rejection_reason,
    )


@router.patch(
    "/doctors/{doctor_id}/toggle-active",
    response_model=ActionResponse,
    summary="Toggle active status of a doctor (suspend/reactivate)",
)
@router.post(
    "/doctors/{doctor_id}/toggle-active",
    response_model=ActionResponse,
    summary="Toggle active status of a doctor (suspend/reactivate)",
)
def toggle_doctor_active(
    doctor_id: str,
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Suspend or reactivate a doctor's account access."""
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found.",
        )

    doctor.is_active = not doctor.is_active
    db.commit()
    status_str = "Active" if doctor.is_active else "Suspended"

    return ActionResponse(
        status="success",
        message=f"{doctor.full_name}'s account status has been set to {status_str}.",
        doctor_id=doctor.doctor_id,
        verification_status=doctor.verification_status,
        verified_at=doctor.verified_at,
    )
