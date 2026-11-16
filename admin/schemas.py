"""
admin/schemas.py
================
Pydantic schemas for Administrator endpoints.
"""

from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, model_validator


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
    username: Optional[str] = None
    email: str
    mobile: str
    medical_degree: str
    registration_number: str
    registration_council: str
    email_verified: bool
    verification_status: str
    is_active: bool
    created_at: datetime
    last_login: Optional[datetime] = None
    has_document: bool
    document_filename: Optional[str] = None
    document_uploaded_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    verified_by: Optional[str] = None
    rejection_reason: Optional[str] = None
    total_assessments: Optional[int] = 0
    total_predictions: Optional[int] = 0


class DoctorRejectionRequest(BaseModel):
    reason: str = Field(..., min_length=5, max_length=512, description="Clinical reason for registration rejection")


class ActionResponse(BaseModel):
    status: str
    message: str
    doctor_id: str
    verification_status: str
    username: Optional[str] = None
    verified_at: Optional[datetime] = None
    approved_at: Optional[datetime] = None
    rejection_reason: Optional[str] = None


# ---------------------------------------------------------------------------
# Admin Forgot & Reset Password Schemas
# ---------------------------------------------------------------------------

class AdminForgotPasswordRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=64, description="Administrator username")
    email: Optional[str] = Field(None, min_length=3, max_length=256, description="Administrator email address")

    @model_validator(mode="after")
    def require_identity(self):
        if not self.username and not self.email:
            raise ValueError("Administrator email is required.")
        return self


class AdminForgotPasswordResponse(BaseModel):
    status: str = "success"
    message: str
    recovery_email_masked: str


class AdminVerifyResetOTPRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=64, description="Administrator username")
    email: Optional[str] = Field(None, min_length=3, max_length=256, description="Administrator email address")
    otp: str = Field(..., min_length=6, max_length=6, description="6-digit verification code")

    @model_validator(mode="after")
    def require_identity(self):
        if not self.username and not self.email:
            raise ValueError("Administrator email is required.")
        return self


class AdminVerifyResetOTPResponse(BaseModel):
    status: str = "verified"
    message: str
    reset_token: str


class AdminResetPasswordRequest(BaseModel):
    username: Optional[str] = Field(None, min_length=2, max_length=64, description="Administrator username")
    email: Optional[str] = Field(None, min_length=3, max_length=256, description="Administrator email address")
    reset_token: Optional[str] = Field(None, description="Reset token from verify-reset-otp")
    otp: Optional[str] = Field(None, min_length=6, max_length=6, description="6-digit verification code")
    new_password: str = Field(..., min_length=8, max_length=128, description="New password")
    confirm_password: str = Field(..., min_length=8, max_length=128, description="Confirm new password")

    @model_validator(mode="after")
    def require_identity(self):
        if not self.username and not self.email:
            raise ValueError("Administrator email is required.")
        return self


# ---------------------------------------------------------------------------
# Admin Dashboard Schemas (Overview & Doctor Activity)
# ---------------------------------------------------------------------------

class AdminOverviewResponse(BaseModel):
    total_doctors: int
    pending_doctors: int
    approved_doctors: int
    rejected_doctors: int
    total_assessments: int
    total_predictions: int


class DoctorActivityView(BaseModel):
    doctor_id: str
    full_name: str
    username: Optional[str] = None
    email: str
    medical_degree: str
    registration_number: str
    verification_status: str
    is_active: bool
    last_login: Optional[datetime] = None
    total_assessments: int
    total_predictions: int


class RecentDoctorRegistration(BaseModel):
    doctor_id: str
    full_name: str
    username: Optional[str] = None
    email: str
    created_at: datetime
    verification_status: str


class RecentActivitySummary(BaseModel):
    recently_logged_in: List[DoctorActivityView]
    recent_verifications: List[DoctorAdminView]
    total_assessments_last_7_days: int
    total_predictions_last_7_days: int
    recent_registrations: List[RecentDoctorRegistration]


class ModelMetricDetail(BaseModel):
    accuracy: float
    precision: float
    sensitivity: float
    specificity: float
    f1_score: float
    auroc: float


class ModelPerformanceResponse(BaseModel):
    logistic_regression: ModelMetricDetail
    artificial_neural_network: ModelMetricDetail
    evaluation_type: str = "10-Fold Stratified Cross-Validation"
    features_used: int = 11
    target_variable: str = "DEATH_EVENT"
    clinical_note: str = "Cross-validation estimates reflect internal retrospective validation on clinical cohort data."
