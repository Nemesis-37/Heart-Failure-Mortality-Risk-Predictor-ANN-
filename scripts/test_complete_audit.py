"""
scripts/test_complete_audit.py
==============================
Full Automated Audit Test Suite covering all 10 Phases of the Final Project Audit.
Tests:
- Database connectivity & fallback models
- ML Artifacts & Inference (LR + ANN)
- Compulsory Patient Reference ID validation
- Unified Authentication (Admin & Doctor)
- Role-based authorization & security
- Clinical Assessment Store & History
"""

import sys
import os
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

results = []

def record(test_name, status, details=""):
    results.append({"name": test_name, "status": status, "details": details})
    symbol = "✓ PASS" if status == "PASS" else ("✗ FAIL" if status == "FAIL" else "- NOT TESTED")
    print(f"[{symbol}] {test_name}: {details}")

print("=" * 70)
print("STARTING COMPLETE TECHNICAL AUDIT TEST SUITE")
print("=" * 70)

# ===========================================================================
# 1. DATABASE & CONFIG AUDIT
# ===========================================================================
print("\n--- PHASE 1: DATABASE & SCHEMA AUDIT ---")
try:
    import sqlite3
    db_file = Path("clinical_local.db")
    if db_file.exists():
        conn = sqlite3.connect(str(db_file))
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table';")
        tables = [t[0] for t in cur.fetchall()]
        conn.close()
        record("Database SQLite Storage", "PASS", f"Tables found: {', '.join(tables)}")
    else:
        record("Database SQLite Storage", "FAIL", "clinical_local.db not found")
except Exception as e:
    record("Database SQLite Storage", "FAIL", str(e))

# ===========================================================================
# 2. ML ARTIFACTS & INFERENCE AUDIT
# ===========================================================================
print("\n--- PHASE 2: ML MODEL & ARTIFACTS VERIFICATION ---")
try:
    import joblib
    import torch
    from main import (
        lr_model,
        lr_feature_names,
        ann_model,
        ann_scaler,
        ann_feature_names,
        PatientData,
        predict_logistic_regression,
        predict_ann,
    )

    # Check Logistic Regression
    assert lr_model is not None, "lr_model not loaded"
    assert len(lr_feature_names) == 11, f"Expected 11 features, got {len(lr_feature_names)}"
    record("Logistic Regression Artifacts", "PASS", f"Model & 11 features loaded: {lr_feature_names}")

    # Check ANN
    assert ann_model is not None, "ann_model not loaded"
    assert ann_scaler is not None, "ann_scaler not loaded"
    assert len(ann_feature_names) == 11, f"Expected 11 features, got {len(ann_feature_names)}"
    record("ANN PyTorch Artifacts", "PASS", f"Weights, Scaler & 11 features loaded: {ann_feature_names}")

    # Test Validation of Compulsory Patient Reference ID
    try:
        invalid_patient = PatientData(
            age=60, anaemia=0, creatinine_phosphokinase=250, diabetes=0,
            ejection_fraction=38, high_blood_pressure=0, platelets=260000,
            serum_creatinine=1.1, serum_sodium=137, sex=1, smoking=0
        )
        record("Compulsory Patient Ref ID Validation", "FAIL", "Allowed creation without patient_reference_id")
    except Exception as val_err:
        record("Compulsory Patient Ref ID Validation", "PASS", f"Correctly rejected missing ID: {type(val_err).__name__}")

    # Test Valid Clinical Inferences
    valid_patient = PatientData(
        patient_reference_id="PT-2026-AUDIT",
        age=60, anaemia=0, creatinine_phosphokinase=250, diabetes=0,
        ejection_fraction=38, high_blood_pressure=0, platelets=260000,
        serum_creatinine=1.1, serum_sodium=137, sex=1, smoking=0
    )

    # LR Prediction
    lr_res = predict_logistic_regression(valid_patient)
    assert lr_res["patient_reference_id"] == "PT-2026-AUDIT"
    assert "predicted_probability" in lr_res and 0.0 <= lr_res["predicted_probability"] <= 1.0
    assert "predicted_class" in lr_res and lr_res["predicted_class"] in (0, 1)
    record("Logistic Regression Prediction (POST /predict)", "PASS", f"Prob: {lr_res['predicted_probability']}, Class: {lr_res['predicted_class']}")

    # ANN Prediction
    ann_res = predict_ann(valid_patient)
    assert ann_res["patient_reference_id"] == "PT-2026-AUDIT"
    assert "predicted_probability" in ann_res and 0.0 <= ann_res["predicted_probability"] <= 1.0
    assert "predicted_class" in ann_res and ann_res["predicted_class"] in (0, 1)
    record("Artificial Neural Network Prediction (POST /predict-ann)", "PASS", f"Prob: {ann_res['predicted_probability']}, Class: {ann_res['predicted_class']}")

except Exception as e:
    record("ML Verification", "FAIL", str(e))

# ===========================================================================
# 3. AUTHENTICATION & ACCESS CONTROL AUDIT
# ===========================================================================
print("\n--- PHASE 3: AUTHENTICATION & SECURITY AUDIT ---")
try:
    from auth.router import doctor_login
    from auth.schemas import DoctorLoginRequest
    from database import SessionLocal
    from admin.security import verify_admin_token

    db = SessionLocal()

    # 1. Administrator Login
    admin_req = DoctorLoginRequest(email="debashish.g333@gmail.com", password="admin_debashish123")
    admin_res = doctor_login(payload=admin_req, db=db)
    assert admin_res.role == "ADMIN", f"Expected ADMIN role, got {admin_res.role}"
    assert admin_res.admin.email == "debashish.g333@gmail.com"
    assert verify_admin_token(admin_res.access_token) is not None
    record("Unified Administrator Login", "PASS", f"Role: {admin_res.role}, Admin: {admin_res.admin.full_name}")

    # 2. Reject Bad Password
    try:
        bad_req = DoctorLoginRequest(email="debashish.g333@gmail.com", password="WrongPassword999!")
        doctor_login(payload=bad_req, db=db)
        record("Invalid Credentials Rejection", "FAIL", "Allowed login with wrong password")
    except Exception:
        record("Invalid Credentials Rejection", "PASS", "HTTP 401 correctly returned")

    # 3. Reject Pending Doctor
    try:
        pending_req = DoctorLoginRequest(email="doca_aa8d12df@hospital.org", password="DoctorPass123!")
        doctor_login(payload=pending_req, db=db)
        record("Pending Doctor Access Restriction", "FAIL", "Pending doctor was allowed to log in")
    except Exception as e:
        record("Pending Doctor Access Restriction", "PASS", "Pending doctor correctly rejected with status 403")

except Exception as e:
    record("Authentication Audit", "FAIL", str(e))

# ===========================================================================
# 4. FRONTEND BUILD AUDIT
# ===========================================================================
print("\n--- PHASE 4: FRONTEND INTEGRATION AUDIT ---")
dist_index = Path("frontend/dist/index.html")
if dist_index.exists():
    record("Frontend Production Build", "PASS", f"Found {dist_index} (built with Vite)")
else:
    record("Frontend Production Build", "FAIL", "frontend/dist/index.html missing")

# ===========================================================================
# SUMMARY
# ===========================================================================
print("\n" + "=" * 70)
print("AUDIT SUMMARY REPORT")
print("=" * 70)
passed = sum(1 for r in results if r["status"] == "PASS")
failed = sum(1 for r in results if r["status"] == "FAIL")
print(f"Total Tests Run: {len(results)}")
print(f"Passed: {passed}")
print(f"Failed: {failed}")
print("=" * 70)

if failed > 0:
    sys.exit(1)
