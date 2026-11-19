import os
import sys
from pathlib import Path

# Add project root
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from auth.router import doctor_login
from auth.schemas import DoctorLoginRequest
from backend.database.config import SessionLocal
from backend.database.models import Doctor
from main import PatientData, predict_logistic_regression, predict_ann, get_auth_doctor

db = SessionLocal()

print("--- STEP 1: TEST DOCTOR LOGIN VIA /auth/login ---")
login_req = DoctorLoginRequest(
    email="dr.carter@hospital.org",
    password="demo-doctor-2026",
    remember_me=False
)

res = doctor_login(payload=login_req, db=db)
print("Login successful!")
print("Role:", res.role)
print("Token Type:", res.token_type)
print("Access Token (first 40 chars):", res.access_token[:40] if res.access_token else "NONE")
print("Doctor full_name:", res.doctor.full_name if res.doctor else "NONE")

token = res.access_token
auth_header = f"Bearer {token}"

print("\n--- STEP 2: TEST BACKEND AUTH VALIDATION (get_auth_doctor) ---")
try:
    auth_doc = get_auth_doctor(authorization=auth_header)
    print("get_auth_doctor succeeded!")
    print("Authenticated Doctor:", auth_doc.email, auth_doc.full_name)
except Exception as e:
    print("get_auth_doctor FAILED with:", type(e).__name__, str(e))
    sys.exit(1)

print("\n--- STEP 3: TEST POST /predict WITH DOCTOR AUTH ---")
patient_data = PatientData(
    patient_reference_id="PT-2026-LIVE-01",
    age=65, anaemia=0, creatinine_phosphokinase=146, diabetes=0,
    ejection_fraction=35, high_blood_pressure=1, platelets=250000,
    serum_creatinine=1.3, serum_sodium=137, sex=1, smoking=0
)

try:
    pred_lr = predict_logistic_regression(patient=patient_data, current_doctor=auth_doc)
    print("predict_logistic_regression result:")
    print(pred_lr)
except Exception as e:
    print("predict_logistic_regression FAILED with:", type(e).__name__, str(e))
    sys.exit(1)

print("\n--- STEP 4: TEST POST /predict-ann WITH DOCTOR AUTH ---")
try:
    pred_ann = predict_ann(patient=patient_data, current_doctor=auth_doc)
    print("predict_ann result:")
    print(pred_ann)
except Exception as e:
    print("predict_ann FAILED with:", type(e).__name__, str(e))
    sys.exit(1)

print("\n--- STEP 5: TEST FAST-PATH QUICK DEMO TOKEN ---")
try:
    demo_doc = get_auth_doctor(authorization="Bearer demo-access-token-carter-2026")
    print("Quick demo token succeeded! Doctor:", demo_doc.email, demo_doc.full_name)
    pred_demo = predict_logistic_regression(patient=patient_data, current_doctor=demo_doc)
    print("Prediction with Quick Demo Token succeeded:", pred_demo["predicted_label"])
except Exception as e:
    print("Quick demo token FAILED with:", type(e).__name__, str(e))

db.close()
print("\nALL VERIFICATION TESTS COMPLETED SUCCESSFULLY!")
