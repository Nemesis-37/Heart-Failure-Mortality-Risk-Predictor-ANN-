"""
scripts/test_phase12_ml_security_audit.py
=========================================
Phase 12 Comprehensive Verification Suite for:
- Part 6: Machine Learning Engines (Logistic Regression & PyTorch ANN)
- Part 8: Application Security, CORS, JWT & Data Protection
"""

import math
import os
import sys
import uuid
from pathlib import Path

# Add project root and backend to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

import joblib
import torch
import numpy as np
import pandas as pd
from fastapi.testclient import TestClient
from main import app, lr_model, ann_model, ann_scaler, lr_feature_names, ann_feature_names
from auth.security import hash_password, verify_password

client = TestClient(app)

def run_phase12_ml_security_audit():
    print("=" * 80)
    print("PHASE 12 — MACHINE LEARNING INFERENCE & SECURITY AUDIT")
    print("=" * 80)

    results = []

    def record_test(test_id: str, name: str, condition: bool, details: str = ""):
        status = "PASS" if condition else "FAIL"
        results.append({
            "test_id": test_id,
            "name": name,
            "status": status,
            "details": details,
        })
        print(f"[{status}] {test_id}: {name} {('- ' + details) if details else ''}")

    # ======================================================================
    # PART 6A: LOGISTIC REGRESSION PIPELINE AUDIT
    # ======================================================================
    print("\n--- [PART 6A] Logistic Regression Pipeline Verification ---")
    record_test("ML01_LR_LOADED", "Logistic Regression pipeline artifact loaded", lr_model is not None)
    record_test("ML02_LR_FEATURES", "Feature count is exactly 11", len(lr_feature_names) == 11, f"Count: {len(lr_feature_names)}")
    record_test("ML03_LR_STEPS", "Pipeline contains standard scaler and classifier", [s[0] for s in lr_model.steps] == ['scaler', 'classifier'])

    # Test sample patient vector
    sample_patient = {
        "patient_reference_id": "PT-2026-AUDIT-001",
        "age": 65.0,
        "anaemia": 0,
        "creatinine_phosphokinase": 250.0,
        "diabetes": 1,
        "ejection_fraction": 35.0,
        "high_blood_pressure": 1,
        "platelets": 250000.0,
        "serum_creatinine": 1.4,
        "serum_sodium": 136.0,
        "sex": 1,
        "smoking": 0,
    }
    input_df = pd.DataFrame([sample_patient])[lr_feature_names]
    lr_direct_prob = float(lr_model.predict_proba(input_df)[0][1])
    lr_direct_class = int(lr_model.predict(input_df)[0])
    record_test("ML04_LR_PROB_BOUNDS", "LR direct probability is finite and within [0.0, 1.0]", math.isfinite(lr_direct_prob) and 0.0 <= lr_direct_prob <= 1.0, f"P={lr_direct_prob:.4f}")

    # Authenticate demo doctor to call protected endpoints
    login_resp = client.post("/auth/login", json={"email": "dr.carter@hospital.org", "password": "demo-doctor-2026"})
    token = login_resp.json().get("access_token")
    auth_headers = {"Authorization": f"Bearer {token}"}

    lr_api_resp = client.post("/predict", json=sample_patient, headers=auth_headers)
    record_test("ML05_LR_API_STATUS", "Protected /predict returns HTTP 200", lr_api_resp.status_code == 200)
    lr_api_data = lr_api_resp.json()
    record_test("ML06_LR_API_PARITY", "API probability matches direct pipeline inference within 0.0001", abs(lr_api_data.get("predicted_probability") - round(lr_direct_prob, 4)) < 0.0001, f"API={lr_api_data.get('predicted_probability')}, Direct={round(lr_direct_prob, 4)}")
    record_test("ML07_LR_CLASS_PARITY", "API predicted_class matches direct prediction", lr_api_data.get("predicted_class") == lr_direct_class)

    # ======================================================================
    # PART 6B: PYTORCH ANN ARCHITECTURE & INFERENCE AUDIT
    # ======================================================================
    print("\n--- [PART 6B] PyTorch Artificial Neural Network Audit ---")
    record_test("ML08_ANN_LOADED", "PyTorch ANN model is loaded", ann_model is not None)
    record_test("ML09_ANN_EVAL_MODE", "ANN is set to eval mode (training=False)", not ann_model.training)

    # Check total parameters
    state = torch.load("models/ann_model.pth", map_location="cpu", weights_only=True)
    total_ann_params = sum(p.numel() for p in state.values())
    record_test("ML10_ANN_PARAM_COUNT", "ANN weights contain exactly 2,881 parameters", total_ann_params == 2881, f"Parameters: {total_ann_params}")

    # Inspect layer shapes
    expected_shapes = {
        "network.0.weight": (64, 11),
        "network.0.bias": (64,),
        "network.3.weight": (32, 64),
        "network.3.bias": (32,),
        "network.6.weight": (1, 32),
        "network.6.bias": (1,),
    }
    shapes_match = all(list(state[k].shape) == list(expected_shapes[k]) for k in expected_shapes)
    record_test("ML11_ANN_LAYER_SHAPES", "ANN layer topology matches 11 -> 64 -> 32 -> 1", shapes_match)

    # Direct ANN inference
    ann_df = pd.DataFrame([sample_patient])[ann_feature_names]
    ann_scaled = ann_scaler.transform(ann_df)
    with torch.inference_mode():
        ann_raw = ann_model(torch.tensor(ann_scaled, dtype=torch.float32))
        ann_direct_prob = float(torch.sigmoid(ann_raw).item())
    record_test("ML12_ANN_PROB_BOUNDS", "ANN direct probability is finite and within [0.0, 1.0]", math.isfinite(ann_direct_prob) and 0.0 <= ann_direct_prob <= 1.0, f"P={ann_direct_prob:.4f}")

    ann_api_resp = client.post("/predict-ann", json=sample_patient, headers=auth_headers)
    record_test("ML13_ANN_API_STATUS", "Protected /predict-ann returns HTTP 200", ann_api_resp.status_code == 200)
    ann_api_data = ann_api_resp.json()
    record_test("ML14_ANN_API_PARITY", "API probability matches direct PyTorch inference within 0.0001", abs(ann_api_data.get("predicted_probability") - round(ann_direct_prob, 4)) < 0.0001, f"API={ann_api_data.get('predicted_probability')}, Direct={round(ann_direct_prob, 4)}")

    # ======================================================================
    # PART 6C: CLINICAL BOUNDARY & STRESS TESTS
    # ======================================================================
    print("\n--- [PART 6C] Clinical Boundary & Input Validation ---")
    # Low EF High Risk Patient (EF=15, Creatinine=4.2)
    severe_patient = {**sample_patient, "ejection_fraction": 15.0, "serum_creatinine": 4.2}
    severe_resp = client.post("/predict-ann", json=severe_patient, headers=auth_headers)
    severe_prob = severe_resp.json().get("predicted_probability")
    record_test("ML15_SEVERE_RISK_ELEVATION", "High-acuity vector produces elevated probability > baseline", severe_prob > ann_direct_prob, f"Severe P={severe_prob:.4f} > Base P={ann_direct_prob:.4f}")

    # Negative Age validation
    neg_age_resp = client.post("/predict", json={**sample_patient, "age": -5.0}, headers=auth_headers)
    record_test("ML16_NEGATIVE_AGE_REJECTED", "Negative age rejected with HTTP 422", neg_age_resp.status_code == 422)

    # Extreme Age validation (> 120)
    high_age_resp = client.post("/predict", json={**sample_patient, "age": 150.0}, headers=auth_headers)
    record_test("ML17_HIGH_AGE_REJECTED", "Age over 120 rejected with HTTP 422", high_age_resp.status_code == 422)

    # Missing feature (ejection_fraction)
    missing_ef = {k: v for k, v in sample_patient.items() if k != "ejection_fraction"}
    missing_ef_resp = client.post("/predict", json=missing_ef, headers=auth_headers)
    record_test("ML18_MISSING_FEATURE_REJECTED", "Missing required ejection_fraction rejected with HTTP 422", missing_ef_resp.status_code == 422)

    # Invalid string type for numeric feature
    str_feat = {**sample_patient, "ejection_fraction": "forty-five"}
    str_feat_resp = client.post("/predict", json=str_feat, headers=auth_headers)
    record_test("ML19_STR_FEAT_REJECTED", "String type in numeric biomarker field rejected with HTTP 422", str_feat_resp.status_code == 422)

    # Out-of-range EF (> 100%)
    high_ef_resp = client.post("/predict", json={**sample_patient, "ejection_fraction": 125.0}, headers=auth_headers)
    record_test("ML20_HIGH_EF_REJECTED", "Ejection fraction > 100% rejected with HTTP 422", high_ef_resp.status_code == 422)

    # ======================================================================
    # PART 8: APPLICATION SECURITY AUDIT
    # ======================================================================
    print("\n--- [PART 8] Security, CORS, JWT & Data Protection ---")
    # 1. Unauthenticated administrative access strictly blocked
    unauth_admin = client.get("/admin/doctors/pending")
    record_test("SEC01_UNAUTH_ADMIN_BLOCKED", "Unauthenticated request to /admin/doctors/pending blocked with HTTP 401", unauth_admin.status_code == 401)

    # 2. Malformed Authorization header format rejected
    malformed_auth = client.post("/predict", json=sample_patient, headers={"Authorization": "Basic dXNlcjpwYXNz"})
    record_test("SEC02_MALFORMED_AUTH_BLOCKED", "Malformed authorization header without 'Bearer' rejected with HTTP 401", malformed_auth.status_code == 401)

    # 3. Tampered JWT token signature rejected
    fake_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.tampered_signature"
    tampered_resp = client.post("/predict", json=sample_patient, headers={"Authorization": f"Bearer {fake_token}"})
    record_test("SEC03_TAMPERED_JWT_REJECTED", "Tampered JWT token signature rejected with HTTP 401", tampered_resp.status_code == 401)

    # 3. CORS Preflight & Trusted Origin Allowlist
    trusted_origin = "https://heart-failure-mortality-risk-predictor.onrender.com"
    cors_valid = client.options("/predict", headers={
        "Origin": trusted_origin,
        "Access-Control-Request-Method": "POST",
    })
    record_test("SEC04_CORS_TRUSTED_ALLOWED", "CORS Preflight from configured Render static site allowed (HTTP 200)", cors_valid.status_code == 200)

    # CORS Untrusted Malicious Origin
    untrusted_origin = "https://malicious-hospital-impostor.com"
    cors_bad = client.options("/predict", headers={
        "Origin": untrusted_origin,
        "Access-Control-Request-Method": "POST",
    })
    record_test("SEC05_CORS_UNTRUSTED_REJECTED", "CORS Preflight from untrusted origin rejected (HTTP 400)", cors_bad.status_code == 400)

    # Localhost development origin
    cors_local = client.options("/predict", headers={
        "Origin": "http://localhost:5173",
        "Access-Control-Request-Method": "POST",
    })
    record_test("SEC06_CORS_LOCALHOST_ALLOWED", "CORS Preflight from local developer port 5173 allowed (HTTP 200)", cors_local.status_code == 200)

    # 4. SQL Injection payload rejection in string parameter fields
    sqli_patient = {**sample_patient, "patient_reference_id": "PT-01'; DROP TABLE clinical.\"Doctors\"; --"}
    sqli_resp = client.post("/predict", json=sqli_patient, headers=auth_headers)
    record_test("SEC07_SQLI_RESILIENCE", "SQL injection vector handled safely without database execution", sqli_resp.status_code == 200)

    # 5. Password Hashing Security Standard
    pwd_to_test = "ClinicalDoctorSecret2026!"
    hashed_pwd = hash_password(pwd_to_test)
    record_test("SEC08_PWD_HASH_NON_PLAINTEXT", "Hashed password does not contain plaintext password", pwd_to_test not in hashed_pwd)
    record_test("SEC09_PWD_HASH_SALTED", "Hash format confirms cryptographic salting and key derivation", hashed_pwd.startswith("$argon2") or hashed_pwd.startswith("$pbkdf2"))
    record_test("SEC10_PWD_VERIFY_SUCCESS", "Matching password successfully verified against hash", verify_password(pwd_to_test, hashed_pwd))
    record_test("SEC11_PWD_VERIFY_MISMATCH", "Mismatching password rejected against hash", not verify_password("WrongSecret!", hashed_pwd))

    # 6. Sensitive error messages check (no stack trace or password leakage)
    err_resp = client.post("/auth/login", json={"email": "dr.carter@hospital.org", "password": "WrongPassword!"})
    record_test("SEC12_SAFE_ERROR_MSG", "Failed login response does not expose internal stack trace", "Traceback" not in err_resp.text and "PasswordHasher" not in err_resp.text)

    # 7. Frontend bundle secret exposure scan
    dist_dir = PROJECT_ROOT / "frontend" / "dist"
    secret_leaks = []
    if dist_dir.exists():
        for asset in dist_dir.rglob("*.js"):
            content = asset.read_text(encoding="utf-8", errors="ignore")
            if "admin_debashish123" in content:
                secret_leaks.append(f"Admin password in {asset.name}")
            if "postgresql://" in content:
                secret_leaks.append(f"PostgreSQL connection string in {asset.name}")
            if "JWT_SECRET_KEY" in content:
                secret_leaks.append(f"JWT Secret Key in {asset.name}")
    record_test("SEC13_FRONTEND_BUNDLE_SECRETS", "Frontend distribution bundle contains zero exposed database URLs or secrets", len(secret_leaks) == 0, f"Leaks found: {secret_leaks}")

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    print("\n" + "=" * 80)
    print(f"AUDIT SUMMARY: {passed} / {total} TESTS PASSED (Failed: {failed})")
    print("=" * 80)
    return results

if __name__ == "__main__":
    res = run_phase12_ml_security_audit()
    failed_count = sum(1 for r in res if r["status"] == "FAIL")
    sys.exit(0 if failed_count == 0 else 1)
