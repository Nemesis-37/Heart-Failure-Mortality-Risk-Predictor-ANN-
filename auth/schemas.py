"""
auth/schemas.py
===============
Pydantic schemas for Doctor registration and response handling.
"""

import re
from datetime import datetime
from typing import Optional
from pydantic import BaseModel, EmailStr, Field, field_validator


class DoctorRegisterRequest(BaseModel):
    full_name: str = Field(..., min_length=3, max_length=128, description="Doctor's full legal name")
    email: EmailStr = Field(..., description="Professional email address")
    mobile: str = Field(..., min_length=7, max_length=32, description="Contact telephone number")
    medical_degree: str = Field(..., min_length=2, max_length=128, description="Degree / qualifications (e.g., MBBS, MD, FACC)")
    registration_number: str = Field(..., min_length=3, max_length=64, description="State or National Medical Council Registration Number")
    registration_council: str = Field(..., min_length=2, max_length=128, description="Issuing Medical Council")
    password: str = Field(..., min_length=8, max_length=128, description="Account password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm password")

    @field_validator("full_name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        clean = v.strip()
        if len(clean) < 3:
            raise ValueError("Full name must be at least 3 characters long.")
        return clean

    @field_validator("email")
    @classmethod
    def normalize_email(cls, v: str) -> str:
        return v.strip().lower()

    @field_validator("password")
    @classmethod
    def validate_password_strength(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters long.")
        if not re.search(r"[A-Z]", v):
            raise ValueError("Password must contain at least one uppercase letter.")
        if not re.search(r"[a-z]", v):
            raise ValueError("Password must contain at least one lowercase letter.")
        if not re.search(r"\d", v):
            raise ValueError("Password must contain at least one number.")
        return v


class DoctorSafeResponse(BaseModel):
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
    document_uploaded: bool

    class Config:
        from_attributes = True


class RegisterSuccessResponse(BaseModel):
    status: str = "success"
    message: str
    doctor: DoctorSafeResponse


class SendOTPRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered doctor email address")


class VerifyOTPRequest(BaseModel):
    email: EmailStr = Field(..., description="Registered doctor email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")

    @field_validator("otp")
    @classmethod
    def validate_otp_digits(cls, v: str) -> str:
        clean = v.strip()
        if not re.match(r"^\d{6}$", clean):
            raise ValueError("OTP must consist of exactly 6 numeric digits.")
        return clean


class OTPResponse(BaseModel):
    status: str
    message: str
    cooldown_seconds: Optional[int] = None
    email: Optional[str] = None
