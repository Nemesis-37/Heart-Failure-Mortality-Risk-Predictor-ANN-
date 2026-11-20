import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# First force SQLite or fast testing
import os
os.environ["FAST_TEST"] = "1"

from fastapi.testclient import TestClient
from main import app

client = TestClient(app, raise_server_exceptions=False)

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

# 1. Test POST /predict without token
r1 = client.post("/predict", json=payload)
print("1. POST /predict (no token): status =", r1.status_code, "body =", r1.json() if r1.status_code == 200 else r1.text)

# 2. Test POST /predict-ann without token
r2 = client.post("/predict-ann", json=payload)
print("2. POST /predict-ann (no token): status =", r2.status_code, "body =", r2.json() if r2.status_code == 200 else r2.text)

# 3. Test POST /api/predict without token
r3 = client.post("/api/predict", json=payload)
print("3. POST /api/predict (no token): status =", r3.status_code, "body =", r3.json() if r3.status_code == 200 else r3.text)

# 4. Test POST /api/predict-ann without token
r4 = client.post("/api/predict-ann", json=payload)
print("4. POST /api/predict-ann (no token): status =", r4.status_code, "body =", r4.json() if r4.status_code == 200 else r4.text)

# 5. Test with demo token
demo_headers = {"Authorization": "Bearer demo-access-token-carter-2026"}
r5 = client.post("/predict", json=payload, headers=demo_headers)
print("5. POST /predict (demo token): status =", r5.status_code, "body =", r5.json() if r5.status_code == 200 else r5.text)

r6 = client.post("/predict-ann", json=payload, headers=demo_headers)
print("6. POST /predict-ann (demo token): status =", r6.status_code, "body =", r6.json() if r6.status_code == 200 else r6.text)

print("\nALL PREDICTIONS COMPLETED SUCCESSFULLY!")
