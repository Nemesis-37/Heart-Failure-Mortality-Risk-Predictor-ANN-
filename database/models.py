"""
database/models.py
==================
SQLAlchemy ORM models for the Heart Failure Mortality Risk Predictor.

These models mirror the tables defined in:
  database/sql_server_assessments_schema.sql

Schema: clinical
Tables:
  - clinical.Doctors      -> Doctor model
  - clinical.Assessments  -> Assessment model
  - clinical.Predictions  -> Prediction model

IMPORTANT: Do NOT modify the column definitions here without also
updating the SQL schema file and creating an Alembic migration.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import (
    DECIMAL,
    BigInteger,
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    SmallInteger,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.mssql import DATETIMEOFFSET, UNIQUEIDENTIFIER
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.config import Base


# ---------------------------------------------------------------------------
# Doctors table  (clinical.Doctors)
# ---------------------------------------------------------------------------

class Doctor(Base):
    """
    Represents a verified medical professional registered in the system.

    Maps to: clinical.Doctors
    """
    __tablename__ = "Doctors"
    __table_args__ = (
        UniqueConstraint("email", name="UQ_Doctors_Email"),
        UniqueConstraint("registration_number", name="UQ_Doctors_RegNumber"),
        CheckConstraint(
            "verification_status IN ('PENDING', 'APPROVED', 'REJECTED')",
            name="CK_Doctors_VerificationStatus",
        ),
        Index("IX_Doctors_Email", "email"),
        Index("IX_Doctors_RegistrationNumber", "registration_number"),
        Index("IX_Doctors_VerificationStatus", "verification_status"),
        {"schema": "clinical"},
    )

    # Primary key — UUID string (NVARCHAR(64) in SQL Server)
    doctor_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    mobile: Mapped[str] = mapped_column(String(32), nullable=False)
    medical_degree: Mapped[str] = mapped_column(String(128), nullable=False)
    registration_number: Mapped[str] = mapped_column(String(64), nullable=False)
    registration_council: Mapped[str] = mapped_column(String(128), nullable=False)
    
    # Verification & Active Flags
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DATETIMEOFFSET,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Administrator Verification Audit Metadata
    verified_at: Mapped[datetime | None] = mapped_column(DATETIMEOFFSET, nullable=True)
    verified_by: Mapped[str | None] = mapped_column(String(64), nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(String(512), nullable=True)

    # Medical registration evidence document metadata (stored securely on disk)
    document_filename: Mapped[str | None] = mapped_column(String(256), nullable=True)
    document_path: Mapped[str | None] = mapped_column(String(512), nullable=True)
    document_uploaded_at: Mapped[datetime | None] = mapped_column(
        DATETIMEOFFSET, nullable=True
    )

    # Relationships
    assessments: Mapped[list["Assessment"]] = relationship(
        "Assessment",
        back_populates="doctor",
        cascade="all, delete-orphan",
    )
    otps: Mapped[list["EmailOTP"]] = relationship(
        "EmailOTP",
        back_populates="doctor",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Doctor id={self.doctor_id!r} name={self.full_name!r}>"


# ---------------------------------------------------------------------------
# EmailOTP table  (clinical.EmailOTP)
# ---------------------------------------------------------------------------

class EmailOTP(Base):
    """
    Stores one-time passwords for doctor email ownership verification.

    Maps to: clinical.EmailOTP
    """
    __tablename__ = "EmailOTP"
    __table_args__ = (
        Index("IX_EmailOTP_DoctorId", "doctor_id", "created_at"),
        Index("IX_EmailOTP_ExpiresAt", "expires_at"),
        {"schema": "clinical"},
    )

    otp_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    doctor_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("clinical.Doctors.doctor_id", ondelete="CASCADE"),
        nullable=False,
    )
    otp_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DATETIMEOFFSET, nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DATETIMEOFFSET,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship back to doctor
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="otps")

    def __repr__(self) -> str:
        return f"<EmailOTP id={self.otp_id!r} doctor={self.doctor_id!r} used={self.is_used}>"


# ---------------------------------------------------------------------------
# Administrators table  (clinical.Administrators)
# ---------------------------------------------------------------------------

class Administrator(Base):
    """
    Stores credentialed hospital administrators who verify doctor registrations.

    Maps to: clinical.Administrators
    """
    __tablename__ = "Administrators"
    __table_args__ = (
        UniqueConstraint("username", name="UQ_Admin_Username"),
        UniqueConstraint("email", name="UQ_Admin_Email"),
        Index("IX_Admin_Email", "email"),
        {"schema": "clinical"},
    )

    admin_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    username: Mapped[str] = mapped_column(String(64), nullable=False)
    email: Mapped[str] = mapped_column(String(256), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    full_name: Mapped[str] = mapped_column(String(128), nullable=False)
    role: Mapped[str] = mapped_column(
        String(64), nullable=False, default="Medical Credentialing Officer"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DATETIMEOFFSET,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    def __repr__(self) -> str:
        return f"<Administrator username={self.username!r} role={self.role!r}>"


# ---------------------------------------------------------------------------
# Assessments table  (clinical.Assessments)
# ---------------------------------------------------------------------------

class Assessment(Base):
    """
    Stores the 11 clinical parameters entered by a doctor for a patient.

    Maps to: clinical.Assessments
    """
    __tablename__ = "Assessments"
    __table_args__ = (
        UniqueConstraint("assessment_code", name="UQ_Assessments_Code"),
        CheckConstraint("age >= 1.0 AND age <= 120.0", name="CK_Assessments_Age"),
        CheckConstraint("anaemia IN (0, 1)", name="CK_Assessments_Anaemia"),
        CheckConstraint(
            "creatinine_phosphokinase > 0.0 AND creatinine_phosphokinase <= 20000.0",
            name="CK_Assessments_CPK",
        ),
        CheckConstraint("diabetes IN (0, 1)", name="CK_Assessments_Diabetes"),
        CheckConstraint(
            "ejection_fraction >= 1.0 AND ejection_fraction <= 100.0",
            name="CK_Assessments_EF",
        ),
        CheckConstraint("high_blood_pressure IN (0, 1)", name="CK_Assessments_HBP"),
        CheckConstraint(
            "platelets > 0.0 AND platelets <= 2000000.0",
            name="CK_Assessments_Platelets",
        ),
        CheckConstraint(
            "serum_creatinine >= 0.1 AND serum_creatinine <= 30.0",
            name="CK_Assessments_Creatinine",
        ),
        CheckConstraint(
            "serum_sodium >= 50.0 AND serum_sodium <= 200.0",
            name="CK_Assessments_Sodium",
        ),
        CheckConstraint("sex IN (0, 1)", name="CK_Assessments_Sex"),
        CheckConstraint("smoking IN (0, 1)", name="CK_Assessments_Smoking"),
        CheckConstraint(
            "predicted_class IS NULL OR predicted_class IN (0, 1)",
            name="CK_Assessments_PredictedClass",
        ),
        CheckConstraint(
            "predicted_probability IS NULL OR "
            "(predicted_probability >= 0.0 AND predicted_probability <= 1.0)",
            name="CK_Assessments_PredictedProb",
        ),
        # Indexes (declared here so Alembic can track them)
        Index("IX_Assessments_PatientRef", "patient_reference_id"),
        Index("IX_Assessments_CreatedAt", "created_at"),
        Index("IX_Assessments_DoctorId", "doctor_id", "created_at"),
        {"schema": "clinical"},
    )

    # Internal UUID primary key (never shown directly in the UI)
    id: Mapped[str] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Public-facing human-readable code, e.g. ASM-2026-0001
    assessment_code: Mapped[str] = mapped_column(String(32), nullable=False)

    # Optional patient reference code, e.g. PT-8942 (NULL = anonymous)
    patient_reference_id: Mapped[str | None] = mapped_column(
        String(64), nullable=True
    )

    # FK to Doctors (nullable — assessment can exist without doctor attribution)
    doctor_id: Mapped[str | None] = mapped_column(
        String(64),
        ForeignKey("clinical.Doctors.doctor_id", ondelete="SET NULL"),
        nullable=True,
    )

    # ---- 11 Clinical Parameters (UCI Heart Failure Dataset) ----
    age: Mapped[float] = mapped_column(DECIMAL(5, 1), nullable=False)
    anaemia: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    creatinine_phosphokinase: Mapped[float] = mapped_column(DECIMAL(8, 2), nullable=False)
    diabetes: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    ejection_fraction: Mapped[float] = mapped_column(DECIMAL(5, 2), nullable=False)
    high_blood_pressure: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    platelets: Mapped[float] = mapped_column(DECIMAL(10, 2), nullable=False)
    serum_creatinine: Mapped[float] = mapped_column(DECIMAL(5, 2), nullable=False)
    serum_sodium: Mapped[float] = mapped_column(DECIMAL(5, 2), nullable=False)
    sex: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    smoking: Mapped[int] = mapped_column(SmallInteger, nullable=False)

    # ---- Model inference tracking (denormalized snapshot) ----
    selected_model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    predicted_class: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    predicted_probability: Mapped[float | None] = mapped_column(
        DECIMAL(6, 4), nullable=True
    )
    prediction_timestamp: Mapped[datetime | None] = mapped_column(
        DATETIMEOFFSET, nullable=True
    )
    is_prediction_stale: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    # ---- Audit timestamps ----
    created_at: Mapped[datetime] = mapped_column(
        DATETIMEOFFSET,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        DATETIMEOFFSET,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationships
    doctor: Mapped["Doctor | None"] = relationship("Doctor", back_populates="assessments")
    predictions: Mapped[list["Prediction"]] = relationship(
        "Prediction",
        back_populates="assessment",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return (
            f"<Assessment code={self.assessment_code!r} "
            f"patient={self.patient_reference_id!r}>"
        )


# ---------------------------------------------------------------------------
# Predictions table  (clinical.Predictions)
# ---------------------------------------------------------------------------

class Prediction(Base):
    """
    Stores an immutable ML model prediction result for an assessment.

    One Assessment can have multiple Prediction records (e.g., one per model run).
    Records are never updated — a new row is inserted for each prediction.

    Maps to: clinical.Predictions
    """
    __tablename__ = "Predictions"
    __table_args__ = (
        UniqueConstraint("prediction_code", name="UQ_Predictions_Code"),
        CheckConstraint("predicted_class IN (0, 1)", name="CK_Predictions_Class"),
        CheckConstraint(
            "predicted_probability >= 0.0 AND predicted_probability <= 1.0",
            name="CK_Predictions_Prob",
        ),
        Index("IX_Predictions_AssessmentId", "assessment_id", "created_at"),
        Index("IX_Predictions_CreatedAt", "created_at"),
        {"schema": "clinical"},
    )

    # Internal UUID primary key
    id: Mapped[str] = mapped_column(
        UNIQUEIDENTIFIER,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    # Public-facing prediction code, e.g. PRD-2026-0001
    prediction_code: Mapped[str] = mapped_column(String(32), nullable=False)

    # FK to parent Assessment
    assessment_id: Mapped[str] = mapped_column(
        UNIQUEIDENTIFIER,
        ForeignKey("clinical.Assessments.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Model details
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    predicted_class: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    predicted_probability: Mapped[float] = mapped_column(DECIMAL(6, 4), nullable=False)
    classification_threshold: Mapped[float] = mapped_column(
        DECIMAL(4, 2), nullable=False, default=0.50
    )
    model_version: Mapped[str] = mapped_column(
        String(32), nullable=False, default="v1.0.0"
    )

    # Audit timestamp
    created_at: Mapped[datetime] = mapped_column(
        DATETIMEOFFSET,
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship
    assessment: Mapped["Assessment"] = relationship(
        "Assessment", back_populates="predictions"
    )

    def __repr__(self) -> str:
        return (
            f"<Prediction code={self.prediction_code!r} "
            f"model={self.model_name!r} class={self.predicted_class}>"
        )
