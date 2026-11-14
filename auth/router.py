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
    DoctorRegisterRequest,
    DoctorSafeResponse,
    OTPResponse,
    RegisterSuccessResponse,
    SendOTPRequest,
    VerifyOTPRequest,
)
from auth.security import hash_password
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
    if now > active_otp.expires_at:
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
