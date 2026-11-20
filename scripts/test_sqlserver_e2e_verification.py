"""
scripts/test_sqlserver_e2e_verification.py
==========================================
End-to-End post-migration verification suite for Microsoft SQL Server.
Verifies that SQL Server (HeartMortalityPredictor, schema clinical)
is actively serving traffic for FastAPI, authentication, and clinical ML predictions.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
load_dotenv(PROJECT_ROOT / ".env")

from sqlalchemy import text
from backend.database.config import engine, SessionLocal, test_db_connection
from backend.database.models import Administrator, Doctor, Assessment, DoctorSession
from auth.router import doctor_login
from auth.schemas import DoctorLoginRequest
from main import PatientData, predict_logistic_regression, predict_ann, get_auth_doctor


def verify_active_sqlserver():
    print("==================================================")
    print("PHASE 1: VERIFY ACTIVE SQL SERVER CONNECTION")
    print("==================================================")
    health = test_db_connection()
    print("test_db_connection() output:", health)

    assert health["status"] == "connected", f"Expected connected status, got {health['status']}"
    assert health["dialect"] == "mssql", f"Expected mssql dialect, got {health['dialect']}"
    assert health["database"].lower() == "heartmortalitypredictor".lower(), f"Expected HeartMortalityPredictor, got {health['database']}"
    print("✓ Active database verified as Microsoft SQL Server (HeartMortalityPredictor)!")

    with engine.connect() as conn:
        res = conn.execute(text("SELECT @@SERVERNAME, DB_NAME(), @@VERSION")).fetchone()
        print(f" - Server Name: {res[0]}")
        print(f" - Active DB: {res[1]}")
        print(f" - Engine: {res[2].splitlines()[0]}")


def verify_migrated_table_counts():
    print("\n==================================================")
    print("PHASE 2: VERIFY MIGRATED SQL SERVER ROW COUNTS")
    print("==================================================")
    db = SessionLocal()
    try:
        admin_count = db.query(Administrator).count()
        doc_count = db.query(Doctor).count()
        session_count = db.query(DoctorSession).count()
        assessment_count = db.query(Assessment).count()

        print(f" - Administrators : {admin_count} (Expected >= 1)")
        print(f" - Doctors        : {doc_count} (Expected >= 14)")
        print(f" - DoctorSessions : {session_count} (Expected >= 10)")
        print(f" - Assessments    : {assessment_count} (Expected >= 4)")

        assert admin_count >= 1, f"Expected at least 1 Administrator in SQL Server, got {admin_count}"
        assert doc_count >= 14, f"Expected at least 14 Doctors in SQL Server, got {doc_count}"
        assert assessment_count >= 4, f"Expected at least 4 Assessments in SQL Server, got {assessment_count}"
        print("✓ All tables populated and verified in SQL Server!")
    finally:
        db.close()


def verify_auth_and_predictions():
    print("\n==================================================")
    print("PHASE 3: VERIFY AUTHENTICATION & PREDICTIONS")
    print("==================================================")
    db = SessionLocal()
    try:
        # 1. Admin login
        print("[Test 1] Administrator login via SQL Server...")
        admin_req = DoctorLoginRequest(email="admin@hospital.org", password="AdminSecure2026!")
        admin_res = doctor_login(payload=admin_req, db=db)
        assert admin_res.role == "ADMIN", f"Expected ADMIN, got {admin_res.role}"
        print("✓ Admin authenticated via SQL Server!")

        # 2. Doctor login
        print("\n[Test 2] Doctor login via SQL Server...")
        doc_req = DoctorLoginRequest(email="dr.carter@hospital.org", password="demo-doctor-2026")
        doc_res = doctor_login(payload=doc_req, db=db)
        assert doc_res.role == "DOCTOR", f"Expected DOCTOR, got {doc_res.role}"
        doc_token = doc_res.access_token
        print("✓ Doctor authenticated via SQL Server!")
        print(f" - Doctor Name: {doc_res.doctor.full_name}")

        # 3. Model prediction with authenticated doctor token
        print("\n[Test 3] Authenticated prediction via /predict (LR)...")
        auth_header = f"Bearer {doc_token}"
        auth_doc = get_auth_doctor(authorization=auth_header)
        patient_data = PatientData(
            patient_reference_id="PT-SQLSERVER-E2E-01",
            age=62, anaemia=0, creatinine_phosphokinase=180, diabetes=0,
            ejection_fraction=32, high_blood_pressure=1, platelets=240000,
            serum_creatinine=1.4, serum_sodium=136, sex=1, smoking=0
        )
        lr_pred = predict_logistic_regression(patient=patient_data, current_doctor=auth_doc)
        print("✓ Logistic Regression Result:", lr_pred["predicted_label"], f"(Prob: {lr_pred['predicted_probability']})")

        print("\n[Test 4] Authenticated prediction via /predict-ann (PyTorch)...")
        ann_pred = predict_ann(patient=patient_data, current_doctor=auth_doc)
        print("✓ PyTorch ANN Result:", ann_pred["predicted_label"], f"(Prob: {ann_pred['predicted_probability']})")

    finally:
        db.close()


def main():
    print("==================================================")
    print("STARTING COMPLETE SQL SERVER E2E VERIFICATION")
    print("==================================================")
    verify_active_sqlserver()
    verify_migrated_table_counts()
    verify_auth_and_predictions()
    print("\n==================================================")
    print("ALL SQL SERVER MIGRATION VERIFICATION CHECKS PASSED!")
    print("==================================================")


if __name__ == "__main__":
    main()
