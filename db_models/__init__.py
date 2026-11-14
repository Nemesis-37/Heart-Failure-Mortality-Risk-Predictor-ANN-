"""
db_models package.

SQLAlchemy database models for Heart Failure Mortality Risk Predictor.
Separated from the ML models/ folder to avoid namespace conflicts.
"""

from db_models.doctor import Doctor
from db_models.otp import EmailOTP

__all__ = ["Doctor", "EmailOTP"]
