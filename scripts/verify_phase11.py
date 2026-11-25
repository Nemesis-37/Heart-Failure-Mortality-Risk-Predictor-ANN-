#!/usr/bin/env python3
"""
Phase 11 Comprehensive Verification Suite
Tests:
1. Health & DB-health endpoints (both root and /api/ prefixes).
2. Model Inference for LR and ANN (/predict, /api/predict, /predict-ann, /api/predict-ann).
3. Prediction validation edge cases (missing fields, boundary values, invalid types).
4. Physician registration (valid practitioner, duplicate registration, validation rejections, file attachment).
5. CORS configuration across Render production subdomains and local origins.
6. Frontend build output inspection (CSS animations, reduced motion, assets).
"""

import sys
import os
import json
import io
import time
from pathlib import Path

# Add project root and backend to path
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR / "backend"))
sys.path.insert(0, str(ROOT_DIR))

os.chdir(ROOT_DIR / "backend")

from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

results = {
    "health_checks": [],
    "inference_checks": [],
    "validation_checks": [],
    "registration_checks": [],
    "cors_checks": [],
    "frontend_build_checks": []
}

def log_test(category: str, name: str, passed: bool, details: str = ""):
    status = "PASS" if passed else "FAIL"
    print(f"[{status}] {category.upper()}: {name} - {details}")
    results[category].append({
        "name": name,
        "passed": passed,
        "details": details
    })

print("=" * 70)
print("PHASE 11 COMPREHENSIVE VERIFICATION SUITE")
print("=" * 70)

# ── 1. Health & DB-Health Endpoints ──────────────────────────────────────────
print("\n--- 1. Health Endpoints ---")
for path in ["/health", "/api/health", "/db-health", "/api/db-health"]:
    try:
        res = client.get(path)
        ok = res.status_code == 200 and "status" in res.json()
        log_test("health_checks", f"GET {path}", ok, f"status={res.status_code}, data={res.json()}")
    except Exception as e:
        log_test("health_checks", f"GET {path}", False, f"Exception: {e}")

# ── 2. Model Inference Endpoints ─────────────────────────────────────────────
print("\n--- 2. Model Inference Endpoints ---")
sample_patient = {
    "age": 65,
    "anaemia": 1,
    "creatinine_phosphokinase": 250,
    "diabetes": 0,
    "ejection_fraction": 35,
    "high_blood_pressure": 1,
    "platelets": 260000,
    "serum_creatinine": 1.4,
    "serum_sodium": 136,
    "sex": 1,
    "smoking": 0,
    "patient_reference_id": "PT-VERIFY-001"
}

inference_targets = [
    ("/predict", "Logistic Regression"),
    ("/api/predict", "Logistic Regression"),
    ("/predict-ann", "Artificial Neural Network"),
    ("/api/predict-ann", "Artificial Neural Network"),
]

for path, expected_model in inference_targets:
    try:
        res = client.post(path, json=sample_patient)
        if res.status_code == 200:
            data = res.json()
            prob = data.get("predicted_probability")
            pred_class = data.get("predicted_class")
            model_name = data.get("model")
            valid = (
                isinstance(prob, (int, float)) and 0.0 <= prob <= 1.0 and
                pred_class in [0, 1] and
                expected_model.lower() in str(model_name).lower()
            )
            log_test("inference_checks", f"POST {path}", valid, f"model={model_name}, prob={prob:.4f}, class={pred_class}")
        else:
            log_test("inference_checks", f"POST {path}", False, f"status={res.status_code}, detail={res.text}")
    except Exception as e:
        log_test("inference_checks", f"POST {path}", False, f"Exception: {e}")

# ── 3. Prediction Input Validation ───────────────────────────────────────────
print("\n--- 3. Prediction Input Validation ---")
# Missing feature
bad_patient_missing = sample_patient.copy()
del bad_patient_missing["ejection_fraction"]
res = client.post("/predict", json=bad_patient_missing)
log_test("validation_checks", "Missing ejection_fraction rejection", res.status_code == 422, f"status={res.status_code}")

# Out-of-range feature
bad_patient_range = sample_patient.copy()
bad_patient_range["age"] = -5
res = client.post("/predict-ann", json=bad_patient_range)
log_test("validation_checks", "Negative age rejection", res.status_code == 422, f"status={res.status_code}")

# Extreme boundary valid patient
boundary_patient = sample_patient.copy()
boundary_patient["age"] = 95
boundary_patient["ejection_fraction"] = 15
boundary_patient["serum_creatinine"] = 9.4
res = client.post("/predict", json=boundary_patient)
log_test("validation_checks", "Extreme clinical boundary acceptance", res.status_code == 200, f"status={res.status_code}")

# ── 4. Physician Registration ────────────────────────────────────────────────
print("\n--- 4. Physician Registration ---")
unique_suffix = int(time.time())
reg_num = f"MED-VERIFY-{unique_suffix % 100000}"
doc_email = f"dr.verify.{unique_suffix}@hospital.org"

form_fields = {
    "full_name": "Dr. Verification Specialist",
    "email": doc_email,
    "mobile": "+1-555-0199",
    "medical_degree": "MD, FACC",
    "registration_number": reg_num,
    "registration_council": "American Board of Internal Medicine",
    "password": "Password123!",
    "confirm_password": "Password123!"
}

# Test registration on both routes (/auth/register and /api/auth/register)
# First: valid registration via /auth/register
try:
    res = client.post("/auth/register", data=form_fields)
    ok = res.status_code in [200, 201] and res.json().get("doctor") is not None
    log_test("registration_checks", "Valid registration via /auth/register", ok, f"status={res.status_code}")
except Exception as e:
    log_test("registration_checks", "Valid registration via /auth/register", False, f"Exception: {e}")

# Duplicate registration rejection (same reg number)
try:
    dup_form = form_fields.copy()
    dup_form["email"] = f"dr.other.{unique_suffix}@hospital.org"
    res = client.post("/auth/register", data=dup_form)
    ok = res.status_code in [400, 409] and ("already registered" in res.text.lower() or "already exists" in res.text.lower())
    log_test("registration_checks", "Duplicate registration_number rejection", ok, f"status={res.status_code}, text={res.text}")
except Exception as e:
    log_test("registration_checks", "Duplicate registration_number rejection", False, f"Exception: {e}")

# Duplicate email rejection
try:
    dup_email_form = form_fields.copy()
    dup_email_form["registration_number"] = f"MED-OTHER-{unique_suffix % 100000}"
    res = client.post("/auth/register", data=dup_email_form)
    ok = res.status_code in [400, 409] and ("already registered" in res.text.lower() or "already exists" in res.text.lower())
    log_test("registration_checks", "Duplicate email rejection", ok, f"status={res.status_code}, text={res.text}")
except Exception as e:
    log_test("registration_checks", "Duplicate email rejection", False, f"Exception: {e}")

# Registration via /api/auth/register with document upload
try:
    doc_email_2 = f"dr.verify.doc.{unique_suffix}@hospital.org"
    reg_num_2 = f"MED-DOC-{unique_suffix % 100000}"
    form_fields_2 = form_fields.copy()
    form_fields_2["email"] = doc_email_2
    form_fields_2["registration_number"] = reg_num_2

    fake_pdf = io.BytesIO(b"%PDF-1.4 ... Fake Medical Degree Certificate ... %%EOF")
    files = {"document": ("credential_certificate.pdf", fake_pdf, "application/pdf")}

    res = client.post("/api/auth/register", data=form_fields_2, files=files)
    ok = res.status_code in [200, 201] and res.json().get("doctor") is not None
    log_test("registration_checks", "Valid registration with PDF document via /api/auth/register", ok, f"status={res.status_code}")
except Exception as e:
    log_test("registration_checks", "Valid registration with PDF document via /api/auth/register", False, f"Exception: {e}")

# Invalid short password rejection
try:
    bad_pwd_form = form_fields.copy()
    bad_pwd_form["email"] = f"dr.badpwd.{unique_suffix}@hospital.org"
    bad_pwd_form["registration_number"] = f"MED-BADPWD-{unique_suffix % 100000}"
    bad_pwd_form["password"] = "short"
    bad_pwd_form["confirm_password"] = "short"
    res = client.post("/auth/register", data=bad_pwd_form)
    ok = res.status_code in [400, 422]
    log_test("registration_checks", "Invalid short password rejection", ok, f"status={res.status_code}")
except Exception as e:
    log_test("registration_checks", "Invalid short password rejection", False, f"Exception: {e}")

# ── 5. CORS Verification ─────────────────────────────────────────────────────
print("\n--- 5. CORS Configuration Verification ---")
cors_origins = [
    ("https://heart-failure-mortality-risk-predictor.onrender.com", True),
    ("https://preview-branch-123.onrender.com", False),
    ("http://localhost:5173", True),
    ("http://127.0.0.1:5173", True),
    ("https://unauthorized-malicious-domain.com", False)
]

for origin, should_allow in cors_origins:
    try:
        headers = {
            "Origin": origin,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "Content-Type,Authorization"
        }
        res = client.options("/predict", headers=headers)
        allow_header = res.headers.get("access-control-allow-origin")
        allowed = (allow_header == origin or allow_header == "*")
        pass_check = allowed if should_allow else not allowed
        log_test("cors_checks", f"CORS Preflight from {origin}", pass_check, f"status={res.status_code}, allowed={allowed}, expected={should_allow}")
    except Exception as e:
        log_test("cors_checks", f"CORS Preflight from {origin}", False, f"Exception: {e}")

# ── 6. Frontend Build & Static Asset Verification ────────────────────────────
print("\n--- 6. Frontend Build & Static Asset Verification ---")
dist_dir = ROOT_DIR / "frontend" / "dist"
index_html = dist_dir / "index.html"
assets_dir = dist_dir / "assets"

log_test("frontend_build_checks", "dist/index.html exists", index_html.exists(), str(index_html))

css_files = list(assets_dir.glob("*.css")) if assets_dir.exists() else []
js_files = list(assets_dir.glob("*.js")) if assets_dir.exists() else []

log_test("frontend_build_checks", "CSS bundle exists", len(css_files) > 0, f"Found: {[f.name for f in css_files]}")
log_test("frontend_build_checks", "JS bundle exists", len(js_files) > 0, f"Found: {[f.name for f in js_files]}")

if css_files:
    css_content = css_files[0].read_text(encoding="utf-8")
    has_visualizer = "med-ai-visualizer-card" in css_content
    has_ecg = "medAiEcgDraw" in css_content
    has_reduced = "prefers-reduced-motion" in css_content
    log_test("frontend_build_checks", "CSS has .med-ai-visualizer-card", has_visualizer, "Medical AI card class found")
    log_test("frontend_build_checks", "CSS has medAiEcgDraw keyframe", has_ecg, "ECG waveform animation found")
    log_test("frontend_build_checks", "CSS has prefers-reduced-motion support", has_reduced, "Reduced motion accessibility rule found")

print("\n" + "=" * 70)
total_tests = sum(len(v) for v in results.values())
total_passed = sum(sum(1 for t in v if t["passed"]) for v in results.values())
print(f"VERIFICATION SUMMARY: {total_passed}/{total_tests} TESTS PASSED")
print("=" * 70)

# Save test summary to JSON
out_path = ROOT_DIR / "scripts" / "phase11_verification_results.json"
out_path.write_text(json.dumps(results, indent=2), encoding="utf-8")
print(f"Saved results to {out_path}")

sys.exit(0 if total_passed == total_tests else 1)
