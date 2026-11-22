import os
import sys
from pathlib import Path
import uuid

# Ensure repository root is on sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

os.environ["ALLOW_SQLITE_OFFLINE"] = "true"
os.environ["APP_ENV"] = "development"

from backend.database.config import SessionLocal, engine
from backend.database.models import Administrator, Doctor
from admin.router import (
    admin_login,
    get_admin_overview,
    list_doctors,
    get_doctor_detail,
    approve_doctor,
    reject_doctor,
    get_doctor_activity,
    get_model_performance,
)
from admin.schemas import AdminLoginRequest, DoctorRejectionRequest
from admin.security import get_current_admin

def run_tests():
    db = SessionLocal()
    try:
        print("=== 1. TEST ADMIN LOGIN & AUTHENTICATION ===")
        login_req = AdminLoginRequest(
            username="debashish.g333@gmail.com",
            password="admin_debashish123",
        )
        login_res = admin_login(login_req, db=db)
        print("Login status:", login_res.status)
        token = login_res.access_token
        print("Admin access token:", token[:25] + "...")
        
        # Verify get_current_admin dependency
        admin_user = get_current_admin(authorization=f"Bearer {token}")
        print("Current admin authenticated:", admin_user.email, "| Username:", admin_user.username)
        assert admin_user.email == "debashish.g333@gmail.com"

        print("\n=== 2. TEST ADMIN OVERVIEW (DATABASE INDICATOR) ===")
        overview = get_admin_overview(current_admin=admin_user, db=db)
        print("Overview statistics:", overview.model_dump())
        assert hasattr(overview, "database_engine")
        print(f"Reported database engine: '{overview.database_engine}'")
        assert overview.database_engine in ("PostgreSQL", "SQLite")

        print("\n=== 3. TEST DOCTOR DIRECTORY: ALL ===")
        docs_all = list_doctors(status_filter="ALL", current_admin=admin_user, db=db)
        print(f"Total doctors loaded (ALL): {len(docs_all)}")
        assert isinstance(docs_all, list)
        assert len(docs_all) > 0

        print("\n=== 4. TEST STATUS FILTERS (APPROVED, PENDING, REJECTED) ===")
        docs_app = list_doctors(status_filter="APPROVED", current_admin=admin_user, db=db)
        print(f"Approved doctors count: {len(docs_app)}")
        for d in docs_app:
            assert d.verification_status == "APPROVED"

        docs_pen = list_doctors(status_filter="PENDING", current_admin=admin_user, db=db)
        print(f"Pending doctors count: {len(docs_pen)}")
        for d in docs_pen:
            assert d.verification_status == "PENDING"

        docs_rej = list_doctors(status_filter="REJECTED", current_admin=admin_user, db=db)
        print(f"Rejected doctors count: {len(docs_rej)}")
        for d in docs_rej:
            assert d.verification_status == "REJECTED"

        print("\n=== 5. TEST DOCTOR SEARCH (NAME, EMAIL, REG NO, USERNAME) ===")
        first_doc = docs_all[0]
        # Search by name
        name_sub = first_doc.full_name[:4]
        s_name = list_doctors(search=name_sub, current_admin=admin_user, db=db)
        assert len(s_name) >= 1
        print(f"Search by name '{name_sub}' returned {len(s_name)} record(s)")

        # Search by email
        email_sub = first_doc.email.split("@")[0]
        s_email = list_doctors(search=email_sub, current_admin=admin_user, db=db)
        assert len(s_email) >= 1
        print(f"Search by email '{email_sub}' returned {len(s_email)} record(s)")

        # Search by registration number
        reg_sub = first_doc.registration_number
        s_reg = list_doctors(search=reg_sub, current_admin=admin_user, db=db)
        assert len(s_reg) >= 1
        print(f"Search by reg no '{reg_sub}' returned {len(s_reg)} record(s)")

        if first_doc.username:
            s_user = list_doctors(search=first_doc.username, current_admin=admin_user, db=db)
            assert len(s_user) >= 1
            print(f"Search by username '{first_doc.username}' returned {len(s_user)} record(s)")

        print("\n=== 6. TEST DOCTOR PROFILE DETAILS, APPROVAL & REJECTION ===")
        test_suffix = uuid.uuid4().hex[:6]
        test_candidate = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name=f"Dr. Candidate {test_suffix}",
            email=f"candidate_{test_suffix}@hospital.org",
            password_hash="mock_hash_for_testing",
            mobile="+1 (555) 019-9999",
            medical_degree="MD, Cardiology",
            registration_number=f"REG-CAN-{test_suffix.upper()}",
            registration_council="National Cardiology Board",
            email_verified=True,
            verification_status="PENDING",
            is_active=True,
        )
        db.add(test_candidate)
        db.commit()
        cand_id = test_candidate.doctor_id

        # Profile detail lookup
        detail = get_doctor_detail(doctor_id=cand_id, current_admin=admin_user, db=db)
        assert detail.doctor_id == cand_id
        assert detail.full_name == f"Dr. Candidate {test_suffix}"
        assert detail.email == f"candidate_{test_suffix}@hospital.org"
        print("Doctor profile details lookup verified:", detail.full_name)

        # Approve candidate
        app_res = approve_doctor(doctor_id=cand_id, current_admin=admin_user, db=db)
        print("Doctor approved:", app_res.status, "| Username:", app_res.username)
        assert app_res.verification_status == "APPROVED"
        assert app_res.username is not None

        # Reject candidate
        rej_res = reject_doctor(
            doctor_id=cand_id,
            payload=DoctorRejectionRequest(reason="License validation mismatch"),
            current_admin=admin_user,
            db=db,
        )
        print("Doctor rejected:", rej_res.status, "| Verification status:", rej_res.verification_status)
        assert rej_res.verification_status == "REJECTED"

        print("\n=== 7. TEST DOCTOR CLINICAL ACTIVITY ANALYTICS ===")
        activities = get_doctor_activity(current_admin=admin_user, db=db)
        print(f"Total doctor activities retrieved: {len(activities)}")
        assert len(activities) > 0
        for act in activities[:3]:
            print(f" - {act.full_name}: assessments={act.total_assessments}, predictions={act.total_predictions}")

        print("\n=== 8. TEST MODEL PERFORMANCE METRICS ===")
        perf = get_model_performance(current_admin=admin_user)
        print(f"Evaluation Type: {perf.evaluation_type}")
        print(f"Logistic Regression AUROC: {perf.logistic_regression.auroc:.4f}")
        print(f"ANN AUROC: {perf.artificial_neural_network.auroc:.4f}")
        assert perf.logistic_regression.auroc > 0.70
        assert perf.artificial_neural_network.auroc > 0.70

        print("\n========================================================")
        print(">>> ALL 8 ADMIN DASHBOARD & WORKFLOW TESTS PASSED! <<<")
        print("========================================================")

    finally:
        db.close()

if __name__ == "__main__":
    run_tests()
