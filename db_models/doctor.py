"""
db_models/doctor.py
===================
SQLAlchemy model for the Doctors table.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, List

from sqlalchemy import Boolean, CheckConstraint, Index, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from db_models.otp import EmailOTP


class Doctor(Base):
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
    )

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
    email_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification_status: Mapped[str] = mapped_column(
        String(32), nullable=False, default="PENDING"
    )
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship to EmailOTP
    otps: Mapped[List["EmailOTP"]] = relationship(
        "EmailOTP",
        back_populates="doctor",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Doctor id={self.doctor_id!r} name={self.full_name!r}>"
