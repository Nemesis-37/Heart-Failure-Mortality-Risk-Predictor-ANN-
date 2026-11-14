"""
db_models/assessment.py
=======================
SQLAlchemy model for the Assessments table.

Stores the 11 clinical model input features evaluated for heart failure
mortality risk estimation. Does not store the 'time' feature to prevent data leakage.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    DECIMAL,
    ForeignKey,
    Index,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from db_models.doctor import Doctor


class Assessment(Base):
    """
    Patient Assessment Model.
    Stores clinical features collected by a verified physician.
    """
    __tablename__ = "Assessments"
    __table_args__ = (
        CheckConstraint("age > 0", name="CK_Assessments_Age_Positive"),
        CheckConstraint("anaemia IN (0, 1)", name="CK_Assessments_Anaemia_Binary"),
        CheckConstraint("diabetes IN (0, 1)", name="CK_Assessments_Diabetes_Binary"),
        CheckConstraint("high_blood_pressure IN (0, 1)", name="CK_Assessments_HBP_Binary"),
        CheckConstraint("sex IN (0, 1)", name="CK_Assessments_Sex_Binary"),
        CheckConstraint("smoking IN (0, 1)", name="CK_Assessments_Smoking_Binary"),
        Index("IX_Assessments_DoctorId_CreatedAt", "doctor_id", "created_at"),
        Index("IX_Assessments_PatientReference", "patient_reference"),
    )

    assessment_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    doctor_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("Doctors.doctor_id", ondelete="CASCADE"),
        nullable=False,
    )
    patient_reference: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )

    # 11 Model Input Features (UCI Heart Failure Dataset - 'time' excluded)
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

    # Optional model prediction tracking fields (nullable if no prediction run yet)
    selected_model: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    predicted_class: Mapped[Optional[int]] = mapped_column(SmallInteger, nullable=True)
    predicted_probability: Mapped[Optional[float]] = mapped_column(DECIMAL(6, 4), nullable=True)

    # Timestamps
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )
    updated_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    # Relationship to Doctor
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="assessments")

    # Compatibility properties for legacy / alternative attribute names
    @property
    def id(self) -> str:
        return self.assessment_id

    @property
    def patient_reference_id(self) -> Optional[str]:
        return self.patient_reference

    @patient_reference_id.setter
    def patient_reference_id(self, value: Optional[str]) -> None:
        self.patient_reference = value

    @property
    def assessment_code(self) -> str:
        return f"ASM-{self.assessment_id[:8].upper()}"

    def __repr__(self) -> str:
        return f"<Assessment id={self.assessment_id!r} doctor={self.doctor_id!r} ref={self.patient_reference!r}>"
