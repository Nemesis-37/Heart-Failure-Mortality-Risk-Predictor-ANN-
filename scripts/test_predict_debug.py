import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from fastapi.testclient import TestClient
from main import app
from auth.session_service import create_access_token

client = TestClient(app)

# 1. Test payload
payload = {
    "patient_reference_id": "PT-2026-TEST",
    "patient_reference": "PT-2026-TEST",
    "age": 65.0,
    "anaemia": 0,
    "creatinine_phosphokinase": 150.0,
    "diabetes": 0,
    "ejection_fraction": 38.0,
    "high_blood_pressure": 0,
    "platelets": 250000.0,
    "serum_creatinine": 1.1,
    "serum_sodium": 137.0,
    "sex": 1,
    "smoking": 0
}

print("--- Testing without token ---")
r_lr_noauth = client.post("/predict", json=payload)
print("POST /predict (no auth):", r_lr_noauth.status_code, r_lr_noauth.text)

r_ann_noauth = client.post("/predict-ann", json=payload)
print("POST /predict-ann (no auth):", r_ann_noauth.status_code, r_ann_noauth.text)

r_api_lr = client.post("/api/predict", json=payload)
print("POST /api/predict (no auth):", r_api_lr.status_code, r_api_lr.text)

r_api_ann = client.post("/api/predict-ann", json=payload)
print("POST /api/predict-ann (no auth):", r_api_ann.status_code, r_api_ann.text)

print("\n--- Testing with demo token ---")
demo_headers = {"Authorization": "Bearer demo-access-token-carter-2026"}
r_demo_lr = client.post("/predict", json=payload, headers=demo_headers)
print("POST /predict (demo token):", r_demo_lr.status_code, r_demo_lr.text)

r_demo_ann = client.post("/predict-ann", json=payload, headers=demo_headers)
print("POST /predict-ann (demo token):", r_demo_ann.status_code, r_demo_ann.text)

print("\n--- Testing with valid JWT token ---")
token = create_access_token(data={"sub": "demo-carter-local-2026", "role": "DOCTOR", "email": "dr.carter@hospital.org"})
jwt_headers = {"Authorization": f"Bearer {token}"}
r_jwt_lr = client.post("/predict", json=payload, headers=jwt_headers)
print("POST /predict (JWT token):", r_jwt_lr.status_code, r_jwt_lr.text)

r_jwt_ann = client.post("/predict-ann", json=payload, headers=jwt_headers)
print("POST /predict-ann (JWT token):", r_jwt_ann.status_code, r_jwt_ann.text)
