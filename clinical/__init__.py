"""
clinical/
=========
Clinical Assessments, Prediction History, and Protected Physician APIs.
"""

from clinical.router import router as clinical_router

__all__ = ["clinical_router"]
