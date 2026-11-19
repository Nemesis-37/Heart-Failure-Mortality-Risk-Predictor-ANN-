import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.database.config import SessionLocal
from backend.database.models import Doctor
from auth.session_service import create_doctor_session, verify_access_token
from auth.dependencies import get_current_doctor
import json
import base64

db = SessionLocal()
doc = db.query(Doctor).filter(Doctor.email == "dr.carter@hospital.org").first()
print("Found doctor in DB:", doc.email, "doctor_id:", doc.doctor_id, "type:", type(doc.doctor_id), "status:", doc.verification_status)

access_token, refresh_token, exp = create_doctor_session(db=db, doctor=doc)
print("\nGenerated access_token:", access_token)

# Step 1: verify_access_token
payload = verify_access_token(access_token)
print("\nverify_access_token payload:", payload)

# Step 2: query doctor
sub_id = payload.get("sub")
print("\nsub_id from payload:", sub_id, "type:", type(sub_id))
fetched_doc = db.query(Doctor).filter(Doctor.doctor_id == sub_id).first()
print("fetched_doc from DB:", fetched_doc)

# Step 3: call get_current_doctor
auth_header = f"Bearer {access_token}"
try:
    current_doc = get_current_doctor(authorization=auth_header, db=db)
    print("\nget_current_doctor SUCCESS! Name:", current_doc.full_name)

    from main import PatientData, predict_logistic_regression, predict_ann, get_auth_doctor
    patient_data = PatientData(
        patient_reference_id="PT-2026-LIVE-01",
        age=65, anaemia=0, creatinine_phosphokinase=146, diabetes=0,
        ejection_fraction=35, high_blood_pressure=1, platelets=250000,
        serum_creatinine=1.3, serum_sodium=137, sex=1, smoking=0
    )
    # Test via get_auth_doctor
    auth_doc_from_header = get_auth_doctor(authorization=auth_header)
    print("get_auth_doctor returned:", auth_doc_from_header.email)
    res_lr = predict_logistic_regression(patient=patient_data, current_doctor=auth_doc_from_header)
    print("predict_logistic_regression succeeded:", res_lr)
    res_ann = predict_ann(patient=patient_data, current_doctor=auth_doc_from_header)
    print("predict_ann succeeded:", res_ann)
except Exception as e:
    print("\nFAILED with:", type(e).__name__, str(e))

db.close()
