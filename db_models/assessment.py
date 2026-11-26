"""
db_models/assessment.py (Compatibility Forwarder)
=================================================
Forwards to backend.database.models.Assessment to guarantee a single central
declarative Base and unified model definition.
"""

from backend.database.models import Assessment

__all__ = ["Assessment"]
