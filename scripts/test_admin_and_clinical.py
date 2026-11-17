"""
scripts/test_admin_and_clinical.py
==================================
Tests Admin Router and Clinical Router functions directly using the DB session.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from database import SessionLocal
from admin.router import get_admin_overview, list_doctors, list_pending_doctors, get_model_performance
from clinical.router import get_doctor_dashboard_stats, list_doctor_assessments, list_prediction_history
from database.models import Administrator, Doctor

db = SessionLocal()
print("=" * 70)
print("TESTING ADMIN AND CLINICAL ROUTER OPERATIONS")
print("=" * 70)

# Mock admin
admin = db.query(Administrator).first()
if not admin:
    # Use SQLite proxy if needed
    class MockAdmin:
        admin_id = "test-admin"
        username = "admin"
        email = "debashish.g333@gmail.com"
        role = "Super Administrator"
    admin = MockAdmin()

# 1. Test Admin Overview
try:
    overview = get_admin_overview(db=db, current_admin=admin)
    print(f"[✓ PASS] Admin Overview: Total Doctors: {overview.total_doctors}, Pending: {overview.pending_doctors}, Approved: {overview.approved_doctors}")
except Exception as e:
    print(f"[✗ FAIL] Admin Overview: {e}")

# 2. Test List Doctors
try:
    doctors = list_doctors(db=db, current_admin=admin, limit=10)
    print(f"[✓ PASS] List Doctors: Retrieved {len(doctors.items) if hasattr(doctors, 'items') else len(doctors)} doctors")
except Exception as e:
    print(f"[✗ FAIL] List Doctors: {e}")

# 3. Test Pending Doctors
try:
    pending = list_pending_doctors(db=db, current_admin=admin)
    print(f"[✓ PASS] List Pending Doctors: Retrieved {len(pending.pending_doctors if hasattr(pending, 'pending_doctors') else pending)} pending doctors")
except Exception as e:
    print(f"[✗ FAIL] List Pending Doctors: {e}")

# 4. Test Model Performance
try:
    perf = get_model_performance(current_admin=admin)
    print(f"[✓ PASS] Model Performance: LR AUROC={perf.logistic_regression.auroc}, ANN AUROC={perf.artificial_neural_network.auroc}")
except Exception as e:
    print(f"[✗ FAIL] Model Performance: {e}")

# 5. Test Doctor Dashboard Stats
try:
    # Mock doctor
    doc = db.query(Doctor).first()
    if not doc:
        class MockDoc:
            doctor_id = "demo-doc"
            email = "dr.carter@hospital.org"
            full_name = "Dr. Julian Carter"
        doc = MockDoc()
    stats = get_doctor_dashboard_stats(db=db, current_doctor=doc)
    print(f"[✓ PASS] Doctor Dashboard Stats: Total Assessments: {stats.total_assessments}, Predictions: {stats.total_predictions}")
except Exception as e:
    print(f"[✗ FAIL] Doctor Dashboard Stats: {e}")

print("=" * 70)
print("COMPLETED ADMIN & CLINICAL ROUTER TESTS")
print("=" * 70)
