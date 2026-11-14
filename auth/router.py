"""
auth/router.py
==============
FastAPI router for Doctor Authentication and Registration.

Endpoints:
- POST /auth/register       : Multipart form-data registration with supporting document
- POST /auth/register-json  : JSON registration for automated API clients
"""

import os
import re
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from auth.email_service import (
    OTP_COOLDOWN_SECONDS,
    OTP_EXPIRY_MINUTES,
    OTP_MAX_ATTEMPTS,
    generate_otp,
    hash_otp,
    send_email_otp,
    verify_otp_hash,
)
from auth.schemas import (
    DoctorLoginRequest,
    DoctorRegisterRequest,
    DoctorSafeResponse,
    LogoutRequest,
    OTPResponse,
    RefreshRequest,
    RegisterSuccessResponse,
    SendOTPRequest,
    TokenResponse,
    VerifyOTPRequest,
)
from auth.security import hash_password, verify_password
from auth.session_service import (
    check_login_rate_limit,
    create_doctor_session,
    record_login_failure,
    reset_login_failures,
    revoke_doctor_session,
    rotate_refresh_token,
)
from auth.validation import validate_doctor_fields
from database.config import get_db
from database.models import Doctor, EmailOTP

router = APIRouter(prefix="/auth", tags=["Doctor Authentication"])

# Storage directory for medical credentials documents
BASE_DIR = Path(__file__).resolve().parent.parent
STORAGE_DIR = BASE_DIR / "storage" / "medical_documents"
STORAGE_DIR.mkdir(parents=True, exist_ok=True)

ALLOWED_EXTENSIONS = {".pdf", ".jpg", ".jpeg", ".png"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB


def _validate_doctor_fields(
    full_name: str,
    email: str,
    mobile: str,
    medical_degree: str,
    registration_number: str,
    registration_council: str,
    password: str,
    confirm_password: str,
):
    """Validate registration parameters and password strength."""
    if not full_name or len(full_name.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Full name must be at least 3 characters long.",
        )

    clean_email = email.strip().lower()
    if not re.match(r"^[^@]+@[^@]+\.[^@]+$", clean_email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format. Please provide a valid professional email.",
        )

    if not mobile or len(mobile.strip()) < 7:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid contact number (minimum 7 digits).",
        )

    if not medical_degree or len(medical_degree.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please specify your medical qualification/degree.",
        )

    if not registration_number or len(registration_number.strip()) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please provide a valid medical council registration number.",
        )

    if not registration_council or len(registration_council.strip()) < 2:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please specify the issuing medical council or licensing authority.",
        )

    if password != confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match. Please verify your password entry.",
        )

    if len(password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long.",
        )
    if not re.search(r"[A-Z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one uppercase letter (A-Z).",
        )
    if not re.search(r"[a-z]", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one lowercase letter (a-z).",
        )
    if not re.search(r"\d", password):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must contain at least one digit (0-9).",
        )

    return clean_email


def _check_duplicates(db: Session, email: str, registration_number: str):
    """Check for existing doctor accounts with duplicate email or registration number."""
    existing_email = db.query(Doctor).filter(Doctor.email == email).first()
    if existing_email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="An account with this email address already exists. Please log in or use another email.",
        )

    clean_reg = registration_number.strip().upper()
    existing_reg = db.query(Doctor).filter(Doctor.registration_number == clean_reg).first()
    if existing_reg:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A doctor with this medical registration number is already registered in the system.",
        )


@router.post(
    "/register",
    response_model=RegisterSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new Doctor with medical credentials",
)
async def register_doctor(
    full_name: str = Form(..., description="Doctor's full name"),
    email: str = Form(..., description="Professional email address"),
    mobile: str = Form(..., description="Contact phone number"),
    medical_degree: str = Form(..., description="Qualification (e.g. MBBS, MD)"),
    registration_number: str = Form(..., description="Medical Registration Number"),
    registration_council: str = Form(..., description="Issuing Medical Council"),
    password: str = Form(..., description="Account password"),
    confirm_password: str = Form(..., description="Confirm password"),
    document: Optional[UploadFile] = File(None, description="Medical registration proof document"),
    db: Session = Depends(get_db),
):
    """
    Register a new physician account.

    Validates:
    - All required fields & password complexity
    - Duplicate email rejection
    - Duplicate medical registration number rejection
    - Argon2id password hashing
    - Secure storage of registration evidence document
    - Default verification_status = 'PENDING'
    """
    clean_email = validate_doctor_fields(
        full_name, email, mobile, medical_degree,
        registration_number, registration_council, password, confirm_password
    )

    _check_duplicates(db, clean_email, registration_number)

    # Process supporting document upload if provided
    doc_filename = None
    doc_rel_path = None
    doc_uploaded_at = None

    if document and document.filename:
        ext = Path(document.filename).suffix.lower()
        if ext not in ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid document format '{ext}'. Allowed file types: PDF, PNG, JPG, JPEG.",
            )

        content = await document.read()
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Document file size exceeds 10MB limit.",
            )

        # Generate unique storage filename
        unique_file_id = f"{uuid.uuid4().hex}_{Path(document.filename).name}"
        dest_path = STORAGE_DIR / unique_file_id
        with open(dest_path, "wb") as f:
            f.write(content)

        doc_filename = document.filename
        doc_rel_path = f"storage/medical_documents/{unique_file_id}"
        doc_uploaded_at = datetime.now(timezone.utc)

    # Hash password with Argon2id
    hashed_pwd = hash_password(password)

    # Create new Doctor in SQL Server
    doctor_id = str(uuid.uuid4())
    new_doctor = Doctor(
        doctor_id=doctor_id,
        full_name=full_name.strip(),
        email=clean_email,
        password_hash=hashed_pwd,
        mobile=mobile.strip(),
        medical_degree=medical_degree.strip(),
        registration_number=registration_number.strip().upper(),
        registration_council=registration_council.strip(),
        email_verified=False,
        verification_status="PENDING",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        document_filename=doc_filename,
        document_path=doc_rel_path,
        document_uploaded_at=doc_uploaded_at,
    )

    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)

    # Immediately issue and dispatch initial verification OTP
    try:
        _issue_and_dispatch_otp(db, new_doctor, enforce_cooldown=False)
    except Exception as exc:
        logger.warning(f"Initial OTP dispatch deferred: {exc}")

    return RegisterSuccessResponse(
        status="success",
        message="Registration submitted successfully. A 6-digit verification code has been sent to your email.",
        doctor=DoctorSafeResponse(
            doctor_id=new_doctor.doctor_id,
            full_name=new_doctor.full_name,
            email=new_doctor.email,
            mobile=new_doctor.mobile,
            medical_degree=new_doctor.medical_degree,
            registration_number=new_doctor.registration_number,
            registration_council=new_doctor.registration_council,
            email_verified=new_doctor.email_verified,
            verification_status=new_doctor.verification_status,
            is_active=new_doctor.is_active,
            created_at=new_doctor.created_at,
            document_uploaded=bool(doc_filename),
        ),
    )


# ---------------------------------------------------------------------------
# Email OTP Internal Helper
# ---------------------------------------------------------------------------

def _issue_and_dispatch_otp(db: Session, doctor: Doctor, enforce_cooldown: bool = True) -> int:
    """
    Generate, hash, store, and dispatch a 6-digit verification code.
    Returns the cooldown seconds for subsequent requests.
    """
    if doctor.email_verified:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Your professional email address is already verified.",
        )

    # Check cooldown against previous OTP
    latest_otp = (
        db.query(EmailOTP)
        .filter(EmailOTP.doctor_id == doctor.doctor_id)
        .order_by(EmailOTP.created_at.desc())
        .first()
    )

    if latest_otp and enforce_cooldown:
        now = datetime.now(timezone.utc)
        elapsed = (now - latest_otp.created_at).total_seconds()
        if elapsed < OTP_COOLDOWN_SECONDS:
            remaining = int(OTP_COOLDOWN_SECONDS - elapsed)
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Please wait {remaining} seconds before requesting a new verification code.",
            )

    # Generate 6-digit OTP
    raw_otp = generate_otp()
    hashed_otp = hash_otp(raw_otp)
    expires_at = datetime.now(timezone.utc) + timedelta(minutes=OTP_EXPIRY_MINUTES)

    new_otp = EmailOTP(
        otp_id=str(uuid.uuid4()),
        doctor_id=doctor.doctor_id,
        otp_hash=hashed_otp,
        expires_at=expires_at,
        attempts=0,
        is_used=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(new_otp)
    db.commit()

    # Dispatch via email
    send_email_otp(doctor.email, doctor.full_name, raw_otp)
    return OTP_COOLDOWN_SECONDS


# ---------------------------------------------------------------------------
# OTP Endpoints
# ---------------------------------------------------------------------------

@router.post(
    "/send-otp",
    response_model=OTPResponse,
    summary="Send or resend email verification OTP",
)
def send_otp_endpoint(payload: SendOTPRequest, db: Session = Depends(get_db)):
    """Send an email verification code to the registered doctor."""
    clean_email = payload.email.strip().lower()
    doctor = db.query(Doctor).filter(Doctor.email == clean_email).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No doctor account found with this email address.",
        )

    cooldown = _issue_and_dispatch_otp(db, doctor, enforce_cooldown=False)
    return OTPResponse(
        status="sent",
        message="A 6-digit verification code has been dispatched to your email address.",
        cooldown_seconds=cooldown,
        email=doctor.email,
    )


@router.post(
    "/resend-otp",
    response_model=OTPResponse,
    summary="Resend verification OTP subject to cooldown",
)
def resend_otp_endpoint(payload: SendOTPRequest, db: Session = Depends(get_db)):
    """Resend verification code with rate-limiting cooldown check."""
    clean_email = payload.email.strip().lower()
    doctor = db.query(Doctor).filter(Doctor.email == clean_email).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No doctor account found with this email address.",
        )

    cooldown = _issue_and_dispatch_otp(db, doctor, enforce_cooldown=True)
    return OTPResponse(
        status="sent",
        message="A new 6-digit verification code has been dispatched to your email address.",
        cooldown_seconds=cooldown,
        email=doctor.email,
    )


@router.post(
    "/verify-otp",
    summary="Validate 6-digit email OTP and mark email verified",
)
def verify_otp_endpoint(payload: VerifyOTPRequest, db: Session = Depends(get_db)):
    """
    Validate the entered 6-digit OTP.

    Rules:
    - Code must match cryptographic hash
    - Code must not be expired (5-minute window)
    - Maximum 5 attempts allowed
    - Upon success, marks email_verified = True
    - verification_status remains PENDING awaiting admin approval
    """
    clean_email = payload.email.strip().lower()
    doctor = db.query(Doctor).filter(Doctor.email == clean_email).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No doctor account found with this email address.",
        )

    if doctor.email_verified:
        return {
            "status": "already_verified",
            "message": "Your email address is already verified.",
            "email_verified": True,
            "verification_status": doctor.verification_status,
        }

    # Fetch latest active OTP
    active_otp = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.doctor_id == doctor.doctor_id,
            EmailOTP.is_used == False,
        )
        .order_by(EmailOTP.created_at.desc())
        .first()
    )

    if not active_otp:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification code found. Please request a new code.",
        )

    now = datetime.now(timezone.utc)

    # Check expiration
    otp_expires = active_otp.expires_at
    if otp_expires and otp_expires.tzinfo is None:
        otp_expires = otp_expires.replace(tzinfo=timezone.utc)

    if otp_expires and now > otp_expires:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification code has expired. Please request a new code.",
        )

    # Check maximum attempt limit
    if active_otp.attempts >= OTP_MAX_ATTEMPTS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum verification attempts exceeded. This code is invalidated. Please request a new code.",
        )

    # Record attempt
    active_otp.attempts += 1

    # Verify cryptographic hash
    is_valid = verify_otp_hash(payload.otp, active_otp.otp_hash)

    if not is_valid:
        db.commit()
        remaining = OTP_MAX_ATTEMPTS - active_otp.attempts
        if remaining <= 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Incorrect verification code. Maximum attempts reached. Code invalidated.",
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Incorrect verification code. {remaining} attempt(s) remaining.",
        )

    # Success: Mark OTP used and Doctor email verified
    active_otp.is_used = True
    doctor.email_verified = True
    # Medical credential status explicitly remains PENDING as required
    db.commit()

    return {
        "status": "verified",
        "message": "Email address successfully verified! Your medical credentials are now awaiting administrative review.",
        "email_verified": True,
        "verification_status": doctor.verification_status,
        "doctor": {
            "doctor_id": doctor.doctor_id,
            "full_name": doctor.full_name,
            "email": doctor.email,
            "registration_number": doctor.registration_number,
            "registration_council": doctor.registration_council,
            "verification_status": doctor.verification_status,
        },
    }


@router.post(
    "/register-json",
    response_model=RegisterSuccessResponse,
    status_code=status.HTTP_201_CREATED,
    summary="JSON registration endpoint for automated API clients",
)
def register_doctor_json(
    payload: DoctorRegisterRequest,
    db: Session = Depends(get_db),
):
    """JSON registration variant without binary file upload."""
    if payload.password != payload.confirm_password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Passwords do not match.",
        )

    clean_email = payload.email.strip().lower()
    _check_duplicates(db, clean_email, payload.registration_number)

    hashed_pwd = hash_password(payload.password)
    doctor_id = str(uuid.uuid4())

    new_doctor = Doctor(
        doctor_id=doctor_id,
        full_name=payload.full_name.strip(),
        email=clean_email,
        password_hash=hashed_pwd,
        mobile=payload.mobile.strip(),
        medical_degree=payload.medical_degree.strip(),
        registration_number=payload.registration_number.strip().upper(),
        registration_council=payload.registration_council.strip(),
        email_verified=False,
        verification_status="PENDING",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db.add(new_doctor)
    db.commit()
    db.refresh(new_doctor)

    return RegisterSuccessResponse(
        status="success",
        message="Registration submitted successfully. Your credentials have been submitted for verification.",
        doctor=DoctorSafeResponse(
            doctor_id=new_doctor.doctor_id,
            full_name=new_doctor.full_name,
            email=new_doctor.email,
            mobile=new_doctor.mobile,
            medical_degree=new_doctor.medical_degree,
            registration_number=new_doctor.registration_number,
            registration_council=new_doctor.registration_council,
            email_verified=new_doctor.email_verified,
            verification_status=new_doctor.verification_status,
            is_active=new_doctor.is_active,
            created_at=new_doctor.created_at,
            document_uploaded=False,
        ),
    )


# ---------------------------------------------------------------------------
# Secure Physician Login & Session Management
# ---------------------------------------------------------------------------

@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Authenticate Doctor and issue secure access & refresh session",
)
def doctor_login(
    payload: DoctorLoginRequest,
    db: Session = Depends(get_db),
):
    """
    Authenticate physician login.

    Strict Clinical Verifications:
    1. Rate limit check (prevents brute-force credential stuffing).
    2. Account exists in SQL Server.
    3. Password hash matches using Argon2id.
    4. Email ownership verified via OTP (email_verified == True).
    5. Medical credentials APPROVED by hospital administration.
    6. Account active (is_active == True).
    """
    clean_email = payload.email.strip().lower()

    # 1. Rate limiting check
    is_allowed, wait_sec = check_login_rate_limit(clean_email)
    if not is_allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many failed login attempts. Please wait {wait_sec} seconds before trying again.",
        )

    # 2. Account existence
    doctor = db.query(Doctor).filter(Doctor.email == clean_email).first()
    if not doctor:
        record_login_failure(clean_email)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password. Please check your credentials.",
        )

    # 3. Password verification
    if not verify_password(payload.password, doctor.password_hash):
        failures = record_login_failure(clean_email)
        remaining = 5 - failures
        detail = "Invalid email or password. Please check your credentials."
        if remaining > 0 and remaining < 3:
            detail += f" ({remaining} attempt(s) remaining before temporary lockout)"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )

    # 4. Check active account status
    if not doctor.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your doctor account has been suspended or deactivated. Please contact hospital administration.",
        )

    # 5. Check email verification
    if not doctor.email_verified:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your professional email address has not been verified. Please enter your 6-digit verification code.",
        )

    # 6. Check administrator approval
    if doctor.verification_status != "APPROVED":
        if doctor.verification_status == "REJECTED":
            reason = doctor.rejection_reason or "Medical council registration details could not be validated."
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Login denied. Your registration was rejected: {reason}",
            )
        else:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Login denied. Your medical council registration is pending administrative review and approval.",
            )

    # Successful login: reset rate limit failures
    reset_login_failures(clean_email)

    # Create short-lived access token and revocable refresh session
    access_token, raw_refresh_token, expires_in = create_doctor_session(
        db=db,
        doctor=doctor,
        remember_me=payload.remember_me,
    )

    return TokenResponse(
        status="success",
        access_token=access_token,
        refresh_token=raw_refresh_token,
        token_type="Bearer",
        expires_in=expires_in,
        doctor=DoctorSafeResponse(
            doctor_id=doctor.doctor_id,
            full_name=doctor.full_name,
            email=doctor.email,
            mobile=doctor.mobile,
            medical_degree=doctor.medical_degree,
            registration_number=doctor.registration_number,
            registration_council=doctor.registration_council,
            email_verified=doctor.email_verified,
            verification_status=doctor.verification_status,
            is_active=doctor.is_active,
            created_at=doctor.created_at,
            document_uploaded=bool(doctor.document_path),
        ),
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Renew access token using valid refresh token (Token Rotation)",
)
def refresh_session_endpoint(payload: RefreshRequest, db: Session = Depends(get_db)):
    """Exchange a valid refresh token for a fresh access token and rotated refresh token."""
    result = rotate_refresh_token(db, payload.refresh_token)
    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Session has expired or was revoked. Please sign in again.",
        )

    new_access_token, new_refresh_token, doctor = result
    return TokenResponse(
        status="success",
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="Bearer",
        expires_in=1800,
        doctor=DoctorSafeResponse(
            doctor_id=doctor.doctor_id,
            full_name=doctor.full_name,
            email=doctor.email,
            mobile=doctor.mobile,
            medical_degree=doctor.medical_degree,
            registration_number=doctor.registration_number,
            registration_council=doctor.registration_council,
            email_verified=doctor.email_verified,
            verification_status=doctor.verification_status,
            is_active=doctor.is_active,
            created_at=doctor.created_at,
            document_uploaded=bool(doctor.document_path),
        ),
    )


@router.post(
    "/logout",
    summary="Revoke active refresh session",
)
def doctor_logout(payload: LogoutRequest, db: Session = Depends(get_db)):
    """Revoke refresh session in SQL Server so it cannot be used again."""
    if payload.refresh_token:
        revoke_doctor_session(db, payload.refresh_token)
    return {"status": "success", "message": "Successfully signed out. Session revoked."}


@router.get(
    "/me",
    response_model=DoctorSafeResponse,
    summary="Get current authenticated physician profile",
)
def get_current_physician_profile(
    current_doctor: Doctor = Depends(
        # Lazy import of dependency to maintain modularity
        lambda: __import__("auth.dependencies", fromlist=["get_current_doctor"]).get_current_doctor
    ),
):
    """Return verified profile of current authenticated physician."""
    return DoctorSafeResponse(
        doctor_id=current_doctor.doctor_id,
        full_name=current_doctor.full_name,
        email=current_doctor.email,
        mobile=current_doctor.mobile,
        medical_degree=current_doctor.medical_degree,
        registration_number=current_doctor.registration_number,
        registration_council=current_doctor.registration_council,
        email_verified=current_doctor.email_verified,
        verification_status=current_doctor.verification_status,
        is_active=current_doctor.is_active,
        created_at=current_doctor.created_at,
        document_uploaded=bool(current_doctor.document_path),
    )
