"""
db_models/doctor.py (Compatibility Forwarder)
=============================================
Forwards to backend.database.models.Doctor to guarantee a single central
declarative Base and unified model definition.
"""

from backend.database.models import Doctor

__all__ = ["Doctor"]
