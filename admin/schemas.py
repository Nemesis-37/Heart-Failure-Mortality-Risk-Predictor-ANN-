"""
admin/schemas.py
================
Pydantic schemas for Administrator endpoints.
"""

from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class AdminLoginRequest(BaseModel):
    username: str = Field(..., description="Administrator username")
    password: str = Field(..., description="Administrator password")


class AdminProfile(BaseModel):
    admin_id: str
    username: str
    email: str
    full_name: str
    role: str


class AdminLoginResponse(BaseModel):
    status: str = "success"
    token: str
    admin: AdminProfile


class DoctorAdminView(BaseModel):
    doctor_id: str
    full_name: str
    email: str
    mobile: str
    medical_degree: str
    registration_number: str
    registration_council: str
    email_verified: bool
    verification_status: str
    is_active: bool
    created_at: datetime
    has_document: bool
    document_filename: Optional[str] = None
    document_uploaded_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    rejection_reason: Optional[str] = None


class DoctorRejectionRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=512, description="Clinical reason for registration rejection")


class ActionResponse(BaseModel):
    status: str
    message: str
    doctor_id: str
    verification_status: str
    verified_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None
