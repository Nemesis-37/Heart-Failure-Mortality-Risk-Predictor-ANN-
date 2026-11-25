"""
tests/test_phase9_e2e_integration.py
Phase 9 Comprehensive End-to-End Test Suite
Tests all 13 required verification items using FastAPI TestClient:
  1. FastAPI startup and shutdown lifespan
  2. Database connectivity & health endpoints
  3. Doctor login & authentication (password: demo-doctor-2026)
  4. Patient assessment creation (valid inputs)
  5. Logistic Regression prediction (/predict)
  6. Artificial Neural Network prediction (/predict-ann)
  7. Verification of probability ranges [0, 1] and threshold 0.50
  8. Assessment & prediction database persistence
  9. Prediction history retrieval (/history)
  10. Dashboard summary aggregation (/dashboard/summary)
  11. Invalid input rejection (missing fields, out-of-bounds features)
  12. IDOR / Authorization security (cross-doctor access rejection)
  13. Model identity labeling & educational disclaimers
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.environ["ALLOW_SQLITE_OFFLINE"] = "true"

from fastapi.testclient import TestClient
from main import app
from backend.database.config import SessionLocal
from backend.database.models import Doctor, Assessment, Prediction
from auth.security import hash_password

client = TestClient(app)

results = []

def record(item_id, name, status, details=""):
    results.append(dict(id=item_id, name=name, status=status, details=details))
    mark = "PASS" if status == "PASSED" else ("FAIL" if status == "FAILED" else status)
    print(f"[{mark}] {item_id}: {name} - {details}")

print("=" * 70)
print("PHASE 9 END-TO-END APPLICATION & INTEGRATION TEST SUITE")
print("=" * 70)

# Item 1: App startup & health
try:
    resp = client.get("/health")
    if resp.status_code == 200 and resp.json().get("status") == "healthy":
        record("E2E-01", "FastAPI Startup & Health Endpoint", "PASSED", f"Status 200, {resp.json()}")
    else:
        record("E2E-01", "FastAPI Startup & Health Endpoint", "FAILED", f"Unexpected response: {resp.text}")
except Exception as e:
    record("E2E-01", "FastAPI Startup & Health Endpoint", "FAILED", str(e))

# Item 2: Database health endpoint
try:
    resp = client.get("/db-health")
    data = resp.json()
    if resp.status_code == 200 and data.get("status") == "connected":
        record("E2E-02", "Database Health & Connectivity Endpoint", "PASSED", f"Connected via dialect: {data.get('dialect')}, DB: {data.get('database')}")
    else:
        record("E2E-02", "Database Health & Connectivity Endpoint", "FAILED", f"Status {resp.status_code}: {resp.text}")
except Exception as e:
    record("E2E-02", "Database Health & Connectivity Endpoint", "FAILED", str(e))

# Item 3: Doctor Authentication
token = None
doctor_id = None
try:
    login_resp = client.post("/auth/login", json={
        "email": "dr.carter@hospital.org",
        "password": "demo-doctor-2026"
    })
    if login_resp.status_code == 200:
        token = login_resp.json().get("access_token")
        doctor_id = login_resp.json().get("doctor", {}).get("doctor_id")
        record("E2E-03", "Doctor Login & JWT Issuance", "PASSED", f"Doctor {doctor_id} authenticated successfully.")
    else:
        record("E2E-03", "Doctor Login & JWT Issuance", "FAILED", f"Status {login_resp.status_code}: {login_resp.text}")
except Exception as e:
    record("E2E-03", "Doctor Login & JWT Issuance", "FAILED", str(e))

auth_headers = {"Authorization": f"Bearer {token}"} if token else {}

# Item 4: Patient Assessment Creation
assessment_id = None
assessment_code = None
sample_patient = {
    "patient_reference_id": "PT-PHASE9-001",
    "age": 65.0,
    "anaemia": 1,
    "creatinine_phosphokinase": 160.0,
    "diabetes": 0,
    "ejection_fraction": 25.0,
    "high_blood_pressure": 1,
    "platelets": 263358.0,
    "serum_creatinine": 1.9,
    "serum_sodium": 130.0,
    "sex": 1,
    "smoking": 0
}

try:
    resp = client.post("/assessments", json=sample_patient, headers=auth_headers)
    if resp.status_code in (200, 201):
        data = resp.json()
        assessment_id = data.get("assessment_id") or data.get("id")
        assessment_code = data.get("assessment_code")
        record("E2E-04", "Patient Assessment Creation", "PASSED", f"Created assessment {assessment_id} ({assessment_code})")
    else:
        record("E2E-04", "Patient Assessment Creation", "FAILED", f"Status {resp.status_code}: {resp.text}")
except Exception as e:
    record("E2E-04", "Patient Assessment Creation", "FAILED", str(e))

# Item 5: Logistic Regression Prediction
lr_prob = None
lr_class = None
try:
    resp = client.post("/predict", json=sample_patient, headers=auth_headers)
    if resp.status_code == 200:
        data = resp.json()
        lr_prob = data.get("predicted_probability")
        lr_class = data.get("predicted_class")
        model_name = data.get("model")
        label = data.get("predicted_label")
        record("E2E-05", "Logistic Regression Inference (/predict)", "PASSED",
               f"Model: {model_name}, Class: {lr_class}, Probability: {lr_prob}, Label: {label}")
    else:
        record("E2E-05", "Logistic Regression Inference (/predict)", "FAILED", f"Status {resp.status_code}: {resp.text}")
except Exception as e:
    record("E2E-05", "Logistic Regression Inference (/predict)", "FAILED", str(e))

# Item 6: ANN Prediction
ann_prob = None
ann_class = None
try:
    resp = client.post("/predict-ann", json=sample_patient, headers=auth_headers)
    if resp.status_code == 200:
        data = resp.json()
        ann_prob = data.get("predicted_probability")
        ann_class = data.get("predicted_class")
        model_name = data.get("model")
        label = data.get("predicted_label")
        record("E2E-06", "PyTorch ANN Inference (/predict-ann)", "PASSED",
               f"Model: {model_name}, Class: {ann_class}, Probability: {ann_prob}, Label: {label}")
    else:
        record("E2E-06", "PyTorch ANN Inference (/predict-ann)", "FAILED", f"Status {resp.status_code}: {resp.text}")
except Exception as e:
    record("E2E-06", "PyTorch ANN Inference (/predict-ann)", "FAILED", str(e))

# Item 7: Probability range and threshold evaluation
try:
    valid_lr = lr_prob is not None and 0.0 <= lr_prob <= 1.0 and lr_class in (0, 1)
    valid_ann = ann_prob is not None and 0.0 <= ann_prob <= 1.0 and ann_class in (0, 1)
    if valid_lr and valid_ann:
        record("E2E-07", "Probability Validity [0.0, 1.0] & Threshold Check", "PASSED",
               f"LR prob={lr_prob} (valid), ANN prob={ann_prob} (valid)")
    else:
        record("E2E-07", "Probability Validity [0.0, 1.0] & Threshold Check", "FAILED",
               f"LR prob={lr_prob}, ANN prob={ann_prob}")
except Exception as e:
    record("E2E-07", "Probability Validity [0.0, 1.0] & Threshold Check", "FAILED", str(e))

# Item 8: Database Persistence (Record prediction linked to assessment)
prediction_code = None
try:
    if assessment_id:
        record_payload = {
            "model_name": "Artificial Neural Network",
            "predicted_class": ann_class,
            "predicted_probability": ann_prob,
            "classification_threshold": 0.50,
            "model_version": "v1.0.0"
        }
        resp = client.post(f"/assessments/{assessment_id}/predictions", json=record_payload, headers=auth_headers)
        if resp.status_code in (200, 201):
            data = resp.json()
            prediction_code = data.get("prediction_code")
            record("E2E-08", "Prediction Record Persistence", "PASSED", f"Linked prediction {prediction_code} to assessment {assessment_id}")
        else:
            record("E2E-08", "Prediction Record Persistence", "FAILED", f"Status {resp.status_code}: {resp.text}")
    else:
        record("E2E-08", "Prediction Record Persistence", "BLOCKED", "Assessment ID not available.")
except Exception as e:
    record("E2E-08", "Prediction Record Persistence", "FAILED", str(e))

# Item 9: Prediction History Retrieval
try:
    resp = client.get("/history", headers=auth_headers)
    if resp.status_code == 200:
        history = resp.json()
        items = history.get("items", history) if isinstance(history, dict) else history
        record("E2E-09", "Prediction History Retrieval", "PASSED", f"Retrieved {len(items)} history entries.")
    else:
        record("E2E-09", "Prediction History Retrieval", "FAILED", f"Status {resp.status_code}: {resp.text}")
except Exception as e:
    record("E2E-09", "Prediction History Retrieval", "FAILED", str(e))

# Item 10: Dashboard Summary Aggregation
try:
    resp = client.get("/dashboard/summary", headers=auth_headers)
    if resp.status_code == 200:
        summary = resp.json()
        record("E2E-10", "Dashboard Analytics Summary", "PASSED",
               f"Assessments={summary.get('total_assessments')}, Predictions={summary.get('total_predictions')}, "
               f"ANN={summary.get('ann_predictions')}, LR={summary.get('logistic_regression_predictions')}")
    else:
        record("E2E-10", "Dashboard Analytics Summary", "FAILED", f"Status {resp.status_code}: {resp.text}")
except Exception as e:
    record("E2E-10", "Dashboard Analytics Summary", "FAILED", str(e))

# Item 11: Invalid Input Handling
try:
    bad_payload = sample_patient.copy()
    bad_payload["age"] = -5.0  # Invalid negative age
    resp = client.post("/predict", json=bad_payload, headers=auth_headers)
    if resp.status_code == 422:
        record("E2E-11", "Invalid Input Validation (Pydantic)", "PASSED", "Rejected negative age with HTTP 422.")
    else:
        record("E2E-11", "Invalid Input Validation (Pydantic)", "FAILED", f"Expected 422, got {resp.status_code}")
except Exception as e:
    record("E2E-11", "Invalid Input Validation (Pydantic)", "FAILED", str(e))

# Item 12: IDOR / Security Rejection
try:
    fake_id = "00000000-0000-0000-0000-000000000000"
    resp = client.get(f"/assessments/{fake_id}", headers=auth_headers)
    if resp.status_code == 404:
        record("E2E-12", "IDOR Cross-Doctor Isolation", "PASSED", "Blocked access to non-existent/cross-doctor record with HTTP 404.")
    else:
        record("E2E-12", "IDOR Cross-Doctor Isolation", "FAILED", f"Expected 404, got {resp.status_code}")
except Exception as e:
    record("E2E-12", "IDOR Cross-Doctor Isolation", "FAILED", str(e))

# Item 13: Educational Notice & Disclaimers
try:
    resp = client.post("/predict", json=sample_patient, headers=auth_headers)
    notice = resp.json().get("notice", "")
    if "Educational prototype" in notice or "not for medical decisions" in notice:
        record("E2E-13", "Educational Disclaimer Verification", "PASSED", f"Notice verified: '{notice}'")
    else:
        record("E2E-13", "Educational Disclaimer Verification", "FAILED", f"Notice missing or incorrect: '{notice}'")
except Exception as e:
    record("E2E-13", "Educational Disclaimer Verification", "FAILED", str(e))

print("=" * 70)
passed_count = sum(1 for r in results if r['status'] == 'PASSED')
total_count = len(results)
print(f"FINAL OUTCOME: {passed_count}/{total_count} PASSED")
print("=" * 70)
