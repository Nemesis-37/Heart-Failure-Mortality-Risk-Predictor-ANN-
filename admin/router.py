"""
admin/router.py
===============
FastAPI router for Hospital Administrator Doctor Credential Verification.

Security:
- All doctor management endpoints are strictly gated by `get_current_admin`.
- Medical evidence documents are streamed securely with session authorization;
  files are never exposed in publicly reachable static URLs.
- Doctors cannot approve themselves.
"""

from datetime import datetime, timezone
from pathlib import Path
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from admin.schemas import (
    ActionResponse,
    AdminLoginRequest,
    AdminLoginResponse,
    AdminProfile,
    DoctorAdminView,
    DoctorRejectionRequest,
)
from admin.security import create_admin_token, get_current_admin
from auth.security import verify_password

try:
    from database import get_db
except ImportError:
    from database.config import get_db

try:
    from db_models import Doctor
except ImportError:
    from database.models import Doctor

from database.models import Administrator

router = APIRouter(prefix="/admin", tags=["Administrator Doctor Verification"])
BASE_DIR = Path(__file__).resolve().parent.parent


@router.post(
    "/login",
    response_model=AdminLoginResponse,
    summary="Hospital Administrator Login",
)
def admin_login(payload: AdminLoginRequest, db: Session = Depends(get_db)):
    """Authenticate administrator credentials and return an authorized session token."""
    username_clean = payload.username.strip()
    admin = db.query(Administrator).filter(Administrator.username == username_clean).first()

    if not admin or not admin.is_active:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid administrator credentials or account disabled.",
        )

    if not verify_password(payload.password, admin.password_hash):
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


@router.get(
    "/doctors",
    response_model=List[DoctorAdminView],
    summary="List doctors filtered by verification status (Admin Only)",
)
def list_doctors(
    status_filter: Optional[str] = Query("PENDING", description="Filter: PENDING, APPROVED, REJECTED, or ALL"),
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """
    List all doctors for clinical credential review.
    Defaults to PENDING doctors awaiting council verification.
    """
    query = db.query(Doctor)

    if status_filter and status_filter.upper() != "ALL":
        query = query.filter(Doctor.verification_status == status_filter.upper())

    doctors = query.order_by(Doctor.created_at.desc()).all()

    return [
        DoctorAdminView(
            doctor_id=doc.doctor_id,
            full_name=doc.full_name,
            email=doc.email,
            mobile=doc.mobile,
            medical_degree=doc.medical_degree,
            registration_number=doc.registration_number,
            registration_council=doc.registration_council,
            email_verified=doc.email_verified,
            verification_status=doc.verification_status,
            is_active=doc.is_active,
            created_at=doc.created_at,
            has_document=bool(doc.document_path and (BASE_DIR / doc.document_path).exists()),
            document_filename=doc.document_filename,
            document_uploaded_at=doc.document_uploaded_at,
            verified_at=doc.verified_at,
            verified_by=doc.verified_by,
            rejection_reason=doc.rejection_reason,
        )
        for doc in doctors
    ]


@router.get(
    "/doctors/pending",
    response_model=List[DoctorAdminView],
    summary="List doctors awaiting verification (Admin Only)",
)
def list_pending_doctors(
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve all doctor accounts awaiting administrative verification (status = 'PENDING')."""
    return list_doctors(status_filter="PENDING", current_admin=current_admin, db=db)


@router.get(
    "/doctors/{doctor_id}",
    response_model=DoctorAdminView,
    summary="Get single doctor credential details (Admin Only)",
)
def get_doctor_detail(
    doctor_id: str,
    current_admin: Administrator = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Retrieve full details of a doctor registration."""
    doctor = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
    if not doctor:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Doctor not found.",
        )

    return DoctorAdminView(
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
        has_document=bool(doctor.document_path and (BASE_DIR / doctor.document_path).exists()),
        document_filename=doctor.document_filename,
        document_uploaded_at=doctor.document_uploaded_at,
        verified_at=doctor.verified_at,
        verified_by=doctor.verified_by,
        rejection_reason=doctor.rejection_reason,
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
    Records decision timestamp and verifying administrator identity.
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

    if doctor.verification_status == "APPROVED":
        return ActionResponse(
            status="already_approved",
            message=f"{doctor.full_name} is already verified and approved.",
            doctor_id=doctor.doctor_id,
            verification_status="APPROVED",
            verified_at=doctor.verified_at,
        )

    now = datetime.now(timezone.utc)
    doctor.verification_status = "APPROVED"
    doctor.verified_at = now
    doctor.verified_by = current_admin.admin_id
    doctor.rejection_reason = None
    db.commit()

    return ActionResponse(
        status="approved",
        message=f"{doctor.full_name} has been approved. Account verification status set to APPROVED.",
        doctor_id=doctor.doctor_id,
        verification_status="APPROVED",
        verified_at=now,
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

    return ActionResponse(
        status="rejected",
        message=f"{doctor.full_name} has been rejected. Reason recorded.",
        doctor_id=doctor.doctor_id,
        verification_status="REJECTED",
        verified_at=now,
        rejection_reason=doctor.rejection_reason,
    )
