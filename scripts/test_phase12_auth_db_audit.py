"""
scripts/test_phase12_auth_db_audit.py
=====================================
Phase 12 Comprehensive Verification Suite for:
- Part 3: Authentication, Physician Registration, Email OTP & Admin Approval
- Part 4: Quick Demo Access Genuine Authentication
- Part 5: Database Schema, Transactions & Persistence
"""

import io
import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root and backend to sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from fastapi.testclient import TestClient
from main import app
from database.config import SessionLocal, engine
from database.models import Base, Doctor, DoctorSession, EmailOTP, Administrator, Assessment, Prediction
from auth.security import hash_password, verify_password

client = TestClient(app)

def run_phase12_auth_db_audit():
    print("=" * 80)
    print("PHASE 12 — AUTHENTICATION, OTP, ADMIN APPROVAL & DATABASE PERSISTENCE AUDIT")
    print("=" * 80)

    db = SessionLocal()
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

    try:
        # Pre-cleanup: ensure test emails are clean
        test_email = "audit.physician.2026@hospital.org"
        test_reg = f"AUDIT-MC-{uuid.uuid4().hex[:6].upper()}"
        dup_email = "audit.duplicate@hospital.org"
        dup_reg = f"AUDIT-MC-DUP-{uuid.uuid4().hex[:6].upper()}"

        audit_emails = [
            test_email,
            dup_email,
            "dr.unapproved.audit@hospital.org",
            "dr.disabled.audit@hospital.org",
            "dr.pdf.audit@hospital.org",
            "dr.rejected.audit@hospital.org",
        ]
        docs = db.query(Doctor).filter(
            (Doctor.email.in_(audit_emails)) |
            (Doctor.registration_number.like("AUDIT-%")) |
            (Doctor.registration_number.like("MC-DIS%")) |
            (Doctor.registration_number.like("MC-UNAPP%"))
        ).all()
        for d in docs:
            db.query(EmailOTP).filter(EmailOTP.doctor_id == d.doctor_id).delete()
            db.query(DoctorSession).filter(DoctorSession.doctor_id == d.doctor_id).delete()
            db.delete(d)
        db.commit()

        # ======================================================================
        # PART 4: QUICK DEMO ACCESS AUDIT
        # ======================================================================
        print("\n--- [PART 4] Quick Demo Access & Seeding Audit ---")
        demo_resp = client.post("/auth/login", json={
            "email": "dr.carter@hospital.org",
            "password": "demo-doctor-2026",
            "remember_me": False,
        })
        record_test("T01_DEMO_LOGIN_HTTP", "Quick Demo Login returns HTTP 200", demo_resp.status_code == 200, f"Status: {demo_resp.status_code}")
        demo_data = demo_resp.json() if demo_resp.status_code == 200 else {}
        record_test("T02_DEMO_ROLE", "Quick Demo Access returns DOCTOR role", demo_data.get("role") == "DOCTOR")
        record_test("T03_DEMO_JWT", "Quick Demo Access issues signed JWT access token", bool(demo_data.get("access_token")))
        record_test("T04_DEMO_PROFILE", "Quick Demo profile contains attending cardiologist credentials", demo_data.get("doctor", {}).get("full_name") == "Dr. Julian Carter, MD")
        record_test("T05_DEMO_STATUS", "Quick Demo account is verified and APPROVED", demo_data.get("doctor", {}).get("verification_status") == "APPROVED")

        # ======================================================================
        # PART 3A: PHYSICIAN LOGIN LIFECYCLE
        # ======================================================================
        print("\n--- [PART 3A] Physician Login Edge Cases ---")
        # Invalid password
        inv_pwd_resp = client.post("/auth/login", json={
            "email": "dr.carter@hospital.org",
            "password": "WrongPassword999!",
        })
        record_test("T06_LOGIN_WRONG_PASSWORD", "Invalid password rejected with HTTP 401", inv_pwd_resp.status_code == 401, f"Status: {inv_pwd_resp.status_code}")

        # Unknown email
        unknown_resp = client.post("/auth/login", json={
            "email": "nonexistent.doctor@unknown.org",
            "password": "Password123!",
        })
        record_test("T07_LOGIN_UNKNOWN_EMAIL", "Unknown email rejected with HTTP 401", unknown_resp.status_code == 401)

        # Unapproved physician
        unapp_reg = f"MC-UNAPP-{uuid.uuid4().hex[:6].upper()}"
        unapp_doc = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. Unapproved Candidate",
            email="dr.unapproved.audit@hospital.org",
            password_hash=hash_password("Password123!"),
            mobile="+15551234567",
            medical_degree="MD",
            registration_number=unapp_reg,
            registration_council="State Council",
            email_verified=True,
            verification_status="PENDING",
            is_active=True,
        )
        db.add(unapp_doc)
        db.commit()

        unapp_login = client.post("/auth/login", json={
            "email": "dr.unapproved.audit@hospital.org",
            "password": "Password123!",
        })
        record_test("T08_LOGIN_UNAPPROVED_BLOCKED", "Unapproved physician login rejected with HTTP 403", unapp_login.status_code == 403, f"Detail: {unapp_login.json().get('detail')}")

        # Disabled account
        dis_reg = f"MC-DIS-{uuid.uuid4().hex[:6].upper()}"
        disabled_doc = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. Disabled Account",
            email="dr.disabled.audit@hospital.org",
            password_hash=hash_password("Password123!"),
            mobile="+15559876543",
            medical_degree="MD",
            registration_number=dis_reg,
            registration_council="State Council",
            email_verified=True,
            verification_status="APPROVED",
            is_active=False,
        )
        db.add(disabled_doc)
        db.commit()

        disabled_login = client.post("/auth/login", json={
            "email": "dr.disabled.audit@hospital.org",
            "password": "Password123!",
        })
        record_test("T09_LOGIN_DISABLED_BLOCKED", "Deactivated/disabled account login rejected with HTTP 403", disabled_login.status_code == 403)

        # ======================================================================
        # PART 3B: PHYSICIAN REGISTRATION
        # ======================================================================
        print("\n--- [PART 3B] Physician Registration Workflow & Validation ---")
        base_reg_payload = {
            "full_name": "Dr. Sarah Jenkins, MD",
            "email": test_email,
            "mobile": "+1 (555) 345-6789",
            "medical_degree": "MD, FACC",
            "registration_number": test_reg,
            "registration_council": "American Board of Internal Medicine",
            "password": "SecurePassword2026!",
            "confirm_password": "SecurePassword2026!",
        }

        # 1. Valid registration
        reg_resp = client.post("/auth/register", data=base_reg_payload)
        record_test("T10_REGISTER_SUCCESS_HTTP", "Valid registration returns HTTP 201 Created", reg_resp.status_code == 201, f"Status: {reg_resp.status_code}")
        reg_data = reg_resp.json() if reg_resp.status_code == 201 else {}
        record_test("T11_REGISTER_UNVERIFIED_STATUS", "Newly registered doctor email_verified is False", reg_data.get("doctor", {}).get("email_verified") is False)
        record_test("T12_REGISTER_PENDING_REVIEW", "Newly registered doctor verification_status is PENDING", reg_data.get("doctor", {}).get("verification_status") == "PENDING")

        # 2. Re-submission resilience (unverified physician updating details before OTP)
        resub_resp = client.post("/auth/register", data=base_reg_payload)
        record_test("T13_REGISTER_RESUBMISSION", "Re-submitting unverified credentials returns 201 without lockout", resub_resp.status_code == 201)

        # 3. Invalid email format
        bad_email_resp = client.post("/auth/register", data={**base_reg_payload, "email": "not-valid-email", "registration_number": "DIFF-REG-01"})
        record_test("T14_REG_BAD_EMAIL", "Malformed email rejected with HTTP 400", bad_email_resp.status_code == 400)

        # 4. Password validation: missing uppercase
        bad_pwd_upper = client.post("/auth/register", data={**base_reg_payload, "email": "valid1@hospital.org", "registration_number": "REG-VAL-01", "password": "password123!", "confirm_password": "password123!"})
        record_test("T15_REG_PWD_NO_UPPER", "Password without uppercase rejected with HTTP 400", bad_pwd_upper.status_code == 400)

        # 5. Password validation: missing digit
        bad_pwd_digit = client.post("/auth/register", data={**base_reg_payload, "email": "valid2@hospital.org", "registration_number": "REG-VAL-02", "password": "Password!", "confirm_password": "Password!"})
        record_test("T16_REG_PWD_NO_DIGIT", "Password without digit rejected with HTTP 400", bad_pwd_digit.status_code == 400)

        # 6. Password validation: too short (< 8 chars)
        bad_pwd_short = client.post("/auth/register", data={**base_reg_payload, "email": "valid3@hospital.org", "registration_number": "REG-VAL-03", "password": "Pass1!", "confirm_password": "Pass1!"})
        record_test("T17_REG_PWD_SHORT", "Password under 8 characters rejected with HTTP 400", bad_pwd_short.status_code == 400)

        # 7. Password mismatch
        mismatch_resp = client.post("/auth/register", data={**base_reg_payload, "email": "valid4@hospital.org", "registration_number": "REG-VAL-04", "confirm_password": "DifferentPassword123!"})
        record_test("T18_REG_PWD_MISMATCH", "Password confirmation mismatch rejected with HTTP 400", mismatch_resp.status_code == 400)

        # 8. Missing required field
        missing_deg = client.post("/auth/register", data={**base_reg_payload, "email": "valid5@hospital.org", "registration_number": "REG-VAL-05", "medical_degree": ""})
        record_test("T19_REG_MISSING_DEGREE", "Missing medical qualification rejected with HTTP 400 or 422", missing_deg.status_code in (400, 422), f"Status: {missing_deg.status_code}")

        # 9. PDF Document upload
        pdf_bytes = b"%PDF-1.4 simulated medical credential registration certificate"
        pdf_resp = client.post(
            "/auth/register",
            data={**base_reg_payload, "email": "dr.pdf.audit@hospital.org", "registration_number": "MC-PDF-AUDIT-99"},
            files={"document": ("credential_license.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        record_test("T20_REG_PDF_UPLOAD", "Valid PDF document upload accepted with HTTP 201", pdf_resp.status_code == 201)
        record_test("T21_REG_PDF_DOCUMENT_FLAG", "Doctor model confirms document_uploaded is True", pdf_resp.json().get("doctor", {}).get("document_uploaded") is True)

        # 10. Invalid document extension (.exe)
        bad_doc_resp = client.post(
            "/auth/register",
            data={**base_reg_payload, "email": "dr.bad_file@hospital.org", "registration_number": "MC-BADFILE-01"},
            files={"document": ("malicious.exe", io.BytesIO(b"binary"), "application/octet-stream")},
        )
        record_test("T22_REG_INVALID_FILE_TYPE", "Disallowed file extension (.exe) rejected with HTTP 400", bad_doc_resp.status_code == 400)

        # ======================================================================
        # PART 3C: EMAIL OTP LIFECYCLE
        # ======================================================================
        print("\n--- [PART 3C] Email OTP Lifecycle & PBKDF2 Hashing ---")
        # Fetch doctor record from database
        doc_record = db.query(Doctor).filter(Doctor.email == test_email).first()
        active_otp = db.query(EmailOTP).filter(EmailOTP.doctor_id == doc_record.doctor_id, EmailOTP.is_used == False).order_by(EmailOTP.created_at.desc()).first()

        record_test("T23_OTP_HASH_STORED", "OTP is hashed before persistence (never plaintext in database)", active_otp.otp_hash.startswith("$otp$v=1$"))
        record_test("T24_OTP_ATTEMPTS_INIT", "New OTP attempts initialized to 0", active_otp.attempts == 0)
        record_test("T25_OTP_EXPIRY_SET", "OTP expires_at is set to future timestamp (~5 mins)", active_otp.expires_at > datetime.now(timezone.utc).replace(tzinfo=None))

        # Test invalid OTP submission
        bad_otp_resp = client.post("/auth/verify-otp", json={"email": test_email, "otp": "000000"})
        record_test("T26_OTP_INVALID_REJECTED", "Incorrect OTP rejected with HTTP 400", bad_otp_resp.status_code == 400)
        db.refresh(active_otp)
        record_test("T27_OTP_ATTEMPT_INCREMENT", "Failed attempt increments attempt counter", active_otp.attempts == 1)

        # Test Resend OTP endpoint
        resend_resp = client.post("/auth/resend-otp", json={"email": test_email})
        record_test("T28_OTP_RESEND_HTTP", "Resend OTP returns HTTP 200", resend_resp.status_code == 200)
        resend_data = resend_resp.json()
        fresh_otp_code = resend_data.get("dev_otp_code")
        record_test("T29_OTP_RESEND_CODE_ISSUED", "Active fresh verification code issued", bool(fresh_otp_code))

        # Verify correct OTP submission
        verify_resp = client.post("/auth/verify-otp", json={"email": test_email, "otp": fresh_otp_code})
        record_test("T30_OTP_VERIFY_SUCCESS", "Submitting matching OTP code returns HTTP 200 OK", verify_resp.status_code == 200)
        record_test("T31_OTP_VERIFY_CONFIRMED", "Response confirms email_verified is True", verify_resp.json().get("email_verified") is True)
        db.refresh(doc_record)
        record_test("T32_OTP_DB_VERIFIED_STATE", "Database Doctor record has email_verified == True", doc_record.email_verified is True)
        record_test("T33_OTP_STATUS_STILL_PENDING", "Doctor verification_status remains PENDING awaiting admin review", doc_record.verification_status == "PENDING")

        # Duplicate registration of verified account rejection
        dup_reg_resp = client.post("/auth/register", data=base_reg_payload)
        record_test("T34_DUP_REG_VERIFIED_REJECTED", "Re-registering already verified account rejected with HTTP 400", dup_reg_resp.status_code == 400)

        # Duplicate registration number rejection
        dup_num_resp = client.post("/auth/register", data={**base_reg_payload, "email": "different.doc@hospital.org"})
        record_test("T35_DUP_REG_NUMBER_REJECTED", "Duplicate medical registration number rejected with HTTP 400", dup_num_resp.status_code == 400)

        # ======================================================================
        # PART 3D: ADMIN APPROVAL WORKFLOW
        # ======================================================================
        print("\n--- [PART 3D] Admin Approval Workflow ---")
        # 1. Admin Login
        admin_login = client.post("/auth/login", json={
            "email": "debashish.g333@gmail.com",
            "password": "admin_debashish123",
        })
        record_test("T36_ADMIN_LOGIN_SUCCESS", "Hospital administrator login returns HTTP 200", admin_login.status_code == 200)
        admin_token = admin_login.json().get("access_token")
        record_test("T37_ADMIN_TOKEN_ISSUED", "Administrator JWT access token issued", bool(admin_token))

        admin_headers = {"Authorization": f"Bearer {admin_token}"}

        # 2. Check pending queue contains verified doctor
        pending_resp = client.get("/admin/doctors/pending", headers=admin_headers)
        record_test("T38_ADMIN_PENDING_QUEUE_HTTP", "Admin pending doctors endpoint returns HTTP 200", pending_resp.status_code == 200)
        pending_raw = pending_resp.json()
        pending_docs = pending_raw.get("doctors", []) if isinstance(pending_raw, dict) else pending_raw
        is_in_pending = any(d.get("email") == test_email for d in pending_docs)
        record_test("T39_ADMIN_DOCTOR_IN_QUEUE", "Doctor with verified email is present in Admin pending review queue", is_in_pending)

        # 3. Prevent unapproved login
        pre_app_login = client.post("/auth/login", json={
            "email": test_email,
            "password": "SecurePassword2026!",
        })
        record_test("T40_PRE_APPROVAL_LOGIN_BLOCKED", "Doctor cannot sign in before administrator approval (HTTP 403)", pre_app_login.status_code == 403)

        # 4. Admin approves doctor
        appr_resp = client.patch(f"/admin/doctors/{doc_record.doctor_id}/approve", headers=admin_headers)
        record_test("T41_ADMIN_APPROVE_HTTP", "Admin approving physician returns HTTP 200 OK", appr_resp.status_code == 200)
        record_test("T42_ADMIN_APPROVE_STATE", "Response confirms verification_status is APPROVED", appr_resp.json().get("verification_status") == "APPROVED")

        # 5. Approved physician logs in
        post_app_login = client.post("/auth/login", json={
            "email": test_email,
            "password": "SecurePassword2026!",
        })
        record_test("T43_POST_APPROVAL_LOGIN_SUCCESS", "Approved physician logs in successfully with HTTP 200", post_app_login.status_code == 200)
        doc_token = post_app_login.json().get("access_token")
        record_test("T44_DOC_JWT_TOKEN", "Approved physician issued valid JWT session token", bool(doc_token))

        # 6. Role-based authorization: Doctor cannot access Admin endpoints
        doc_headers = {"Authorization": f"Bearer {doc_token}"}
        unauth_admin_resp = client.get("/admin/doctors/pending", headers=doc_headers)
        record_test("T45_RBAC_DOCTOR_BLOCKED_FROM_ADMIN", "Physician token rejected from Admin routes with HTTP 403 Forbidden", unauth_admin_resp.status_code == 403)

        # 7. Doctor Logout
        logout_resp = client.post("/auth/logout", headers=doc_headers, json={})
        record_test("T46_LOGOUT_SUCCESS", "Physician logout returns HTTP 200 OK", logout_resp.status_code == 200)

        # ======================================================================
        # PART 5: DATABASE PERSISTENCE & ASSESSMENTS AUDIT
        # ======================================================================
        print("\n--- [PART 5] Database Schema & Clinical Data Persistence ---")
        # 1. Verify all 6 tables exist in metadata
        required_tables = {"clinical.Doctors", "clinical.DoctorSessions", "clinical.EmailOTP", "clinical.Administrators", "clinical.Assessments", "clinical.Predictions"}
        existing_tables = set(Base.metadata.tables.keys())
        record_test("T47_DB_ALL_TABLES_DEFINED", "All 6 required clinical tables mapped in metadata", required_tables.issubset(existing_tables))

        # 2. Create synthetic patient assessment
        sample_assessment_code = f"ASM-AUDIT-{uuid.uuid4().hex[:6].upper()}"
        new_assessment = Assessment(
            id=str(uuid.uuid4()),
            assessment_code=sample_assessment_code,
            patient_reference_id="PT-998811",
            doctor_id=doc_record.doctor_id,
            age=67.0,
            anaemia=0,
            creatinine_phosphokinase=350.0,
            diabetes=1,
            ejection_fraction=28.0,
            high_blood_pressure=1,
            platelets=210000.0,
            serum_creatinine=1.9,
            serum_sodium=134.0,
            sex=1,
            smoking=0,
            selected_model="ANN",
            predicted_class=1,
            predicted_probability=0.4850,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_assessment)
        db.commit()
        db.refresh(new_assessment)
        record_test("T48_DB_ASSESSMENT_PERSIST", "Patient assessment successfully committed to database", bool(new_assessment.id))

        # 3. Create synthetic prediction linked to assessment
        sample_pred_code = f"PRD-AUDIT-{uuid.uuid4().hex[:6].upper()}"
        new_pred = Prediction(
            id=str(uuid.uuid4()),
            prediction_code=sample_pred_code,
            assessment_id=new_assessment.id,
            model_name="Artificial Neural Network",
            predicted_class=1,
            predicted_probability=0.4850,
            classification_threshold=0.50,
            model_version="v1.0.0",
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_pred)
        db.commit()
        db.refresh(new_pred)
        record_test("T49_DB_PREDICTION_PERSIST", "Linked prediction record committed to database", bool(new_pred.id))

        # 4. Query back assessment and prediction to test foreign-key and persistence
        db.expire_all()
        queried_ass = db.query(Assessment).filter(Assessment.assessment_code == sample_assessment_code).first()
        record_test("T50_DB_DATA_INTEGRITY", "Queried assessment matches committed clinical parameters", queried_ass and float(queried_ass.age) == 67.0 and float(queried_ass.ejection_fraction) == 28.0)

    finally:
        # Step 11: Teardown test accounts to maintain pristine database state
        try:
            for test_clean_doc in [test_email, "dr.unapproved.audit@hospital.org", "dr.disabled.audit@hospital.org", "dr.pdf.audit@hospital.org"]:
                to_delete = db.query(Doctor).filter(Doctor.email == test_clean_doc).all()
                for td in to_delete:
                    db.query(EmailOTP).filter(EmailOTP.doctor_id == td.doctor_id).delete()
                    db.query(DoctorSession).filter(DoctorSession.doctor_id == td.doctor_id).delete()
                    db.delete(td)
            # Delete synthetic test assessment and prediction
            test_ass = db.query(Assessment).filter(Assessment.patient_reference_id == "PT-998811").all()
            for ta in test_ass:
                db.query(Prediction).filter(Prediction.assessment_id == ta.id).delete()
                db.delete(ta)
            db.commit()
        except Exception as e:
            print(f"Cleanup warning: {e}")
        db.close()

    total = len(results)
    passed = sum(1 for r in results if r["status"] == "PASS")
    failed = sum(1 for r in results if r["status"] == "FAIL")

    print("\n" + "=" * 80)
    print(f"AUDIT SUMMARY: {passed} / {total} TESTS PASSED (Failed: {failed})")
    print("=" * 80)
    return results

if __name__ == "__main__":
    res = run_phase12_auth_db_audit()
    failed_count = sum(1 for r in res if r["status"] == "FAIL")
    sys.exit(0 if failed_count == 0 else 1)
