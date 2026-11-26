"""
db_models/otp.py (Compatibility Forwarder)
==========================================
Forwards to backend.database.models.EmailOTP to guarantee a single central
declarative Base and unified model definition.
"""

from backend.database.models import EmailOTP

__all__ = ["EmailOTP"]
