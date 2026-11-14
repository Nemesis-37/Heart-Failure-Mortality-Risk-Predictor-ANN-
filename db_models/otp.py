"""
db_models/otp.py
================
SQLAlchemy model for the EmailOTP table.
"""

import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy import Boolean, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base

if TYPE_CHECKING:
    from db_models.doctor import Doctor


class EmailOTP(Base):
    __tablename__ = "EmailOTP"
    __table_args__ = (
        Index("IX_EmailOTP_DoctorId", "doctor_id"),
        Index("IX_EmailOTP_ExpiresAt", "expires_at"),
    )

    otp_id: Mapped[str] = mapped_column(
        String(64),
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )
    doctor_id: Mapped[str] = mapped_column(
        String(64),
        ForeignKey("Doctors.doctor_id", ondelete="CASCADE"),
        nullable=False,
    )
    otp_hash: Mapped[str] = mapped_column(String(256), nullable=False)
    expires_at: Mapped[datetime] = mapped_column(nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    is_used: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(
        nullable=False,
        default=lambda: datetime.now(timezone.utc),
    )

    # Relationship back to Doctor
    doctor: Mapped["Doctor"] = relationship("Doctor", back_populates="otps")

    def __repr__(self) -> str:
        return f"<EmailOTP id={self.otp_id!r} doctor={self.doctor_id!r} used={self.is_used}>"
