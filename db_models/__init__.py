"""
db_models package (Compatibility Forwarder).
============================================
Forward to backend.database.models to ensure a single central declarative Base
and unified ORM model definitions across the entire application.
"""

from backend.database.models import (
    Administrator,
    Assessment,
    Doctor,
    DoctorSession,
    EmailOTP,
    Prediction,
)

__all__ = [
    "Administrator",
    "Assessment",
    "Doctor",
    "DoctorSession",
    "EmailOTP",
    "Prediction",
]
