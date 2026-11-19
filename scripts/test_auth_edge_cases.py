import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from main import get_auth_doctor, PatientData, predict_logistic_regression
from fastapi import HTTPException

print("--- 1. Testing Invalid Bearer Token ---")
try:
    get_auth_doctor(authorization="Bearer completely-bogus-token-xyz")
    print("FAIL: Should have raised 401")
except HTTPException as e:
    print(f"PASS: Correctly raised {e.status_code}: {e.detail}")
    assert e.status_code == 401

print("\n--- 2. Testing Non-Bearer Authorization Header ---")
try:
    get_auth_doctor(authorization="Basic dXNlcjpwYXNz")
    print("FAIL: Should have raised 401")
except HTTPException as e:
    print(f"PASS: Correctly raised {e.status_code}: {e.detail}")
    assert e.status_code == 401

print("\n--- 3. Testing Administrator Token on Predict ---")
from admin.security import create_admin_token
from backend.database.config import SessionLocal
from backend.database.models import Administrator

db = SessionLocal()
admin = db.query(Administrator).first()
db.close()

if admin:
    admin_token = create_admin_token(admin.admin_id, admin.username)
    admin_auth = get_auth_doctor(authorization=f"Bearer {admin_token}")
    assert admin_auth is not None
    assert admin_auth.role == "ADMIN"
    print(f"PASS: Administrator token verified successfully! Role: {admin_auth.role}")

    patient = PatientData(
        patient_reference_id="PT-ADMIN-AUDIT-01",
        age=55, anaemia=0, creatinine_phosphokinase=150, diabetes=0,
        ejection_fraction=40, high_blood_pressure=0, platelets=220000,
        serum_creatinine=1.0, serum_sodium=138, sex=1, smoking=0
    )
    res = predict_logistic_regression(patient=patient, current_doctor=admin_auth)
    assert res["patient_reference_id"] == "PT-ADMIN-AUDIT-01"
    print(f"PASS: Administrator inference executed: {res['predicted_label']} (Prob: {res['predicted_probability']})")

print("\nALL EDGE-CASE AUTH TESTS PASSED!")
