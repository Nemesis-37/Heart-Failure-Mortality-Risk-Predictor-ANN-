"""
scripts/test_signup_end_to_end_validation.py
============================================
Comprehensive End-to-End Validation for Physician Signup,
Email OTP Generation & Verification, Admin Review Queue, and Login Flow.
"""

import io
import os
import sys
from pathlib import Path

# Ensure project root is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "backend"))

from fastapi.testclient import TestClient
from main import app
from backend.database.config import SessionLocal
from backend.database.models import Administrator, Doctor, EmailOTP
from auth.security import hash_password

client = TestClient(app)

def run_tests():
    print("=" * 70)
    print("STARTING PHYSICIAN SIGNUP & EMAIL OTP END-TO-END VALIDATION AUDIT")
    print("=" * 70)

    db = SessionLocal()
    passed = 0
    total = 0

    def check(title: str, condition: bool, extra: str = ""):
        nonlocal passed, total
        total += 1
        status_str = "PASS" if condition else "FAIL"
        print(f"[{status_str}] Test {total:02d}: {title} {('- ' + extra) if extra else ''}")
        if not condition:
            print(f"   FAILED ASSERTION DETAILS: {extra}")
        else:
            passed += 1

    try:
        # Step 0: Clean up any prior test Debashish Giri records to test from clean slate
        test_email = "debashish.g333@gmail.com"
        test_reg_num = "MC-12-2005"
        prior_docs = db.query(Doctor).filter((Doctor.email == test_email) | (Doctor.registration_number == test_reg_num)).all()
        for doc in prior_docs:
            db.query(EmailOTP).filter(EmailOTP.doctor_id == doc.doctor_id).delete()
            db.delete(doc)
        db.commit()

        # TEST 1: Initial Physician Registration with exact credentials
        print("\n--- Phase 1: User Exact Credentials Submission ---")
        reg_payload = {
            "full_name": "DEBASHISH GIRI",
            "email": test_email,
            "mobile": "+91 6396570478",
            "medical_degree": "mbbs",
            "registration_number": test_reg_num,
            "registration_council": "std , bengaluru",
            "password": "Password123!",
            "confirm_password": "Password123!",
        }

        resp1 = client.post("/auth/register", data=reg_payload)
        check("Initial Registration Status Code is 201", resp1.status_code == 201, f"Status: {resp1.status_code}")
        body1 = resp1.json()
        check("Registration response status is 'success'", body1.get("status") == "success")
        check("Registration returns dev_otp_code in dev mode", bool(body1.get("dev_otp_code")), f"dev_otp: {body1.get('dev_otp_code')}")
        check("Doctor email_verified is False upon initial registration", body1.get("doctor", {}).get("email_verified") is False)
        check("Doctor verification_status is PENDING", body1.get("doctor", {}).get("verification_status") == "PENDING")
        initial_otp = body1.get("dev_otp_code")

        # TEST 2: Re-submission of unverified account (Resilience Test)
        print("\n--- Phase 2: Unverified Physician Re-Submission Resilience ---")
        # Previously, submitting again when unverified threw 400 Bad Request duplicate account error.
        # Now it should seamlessly update and issue a fresh OTP code!
        resp2 = client.post("/auth/register", data=reg_payload)
        check("Re-submitting unverified account returns 201 Created (No 400 lockout)", resp2.status_code == 201, f"Status: {resp2.status_code}")
        body2 = resp2.json()
        check("Re-submission generates fresh dev_otp_code", bool(body2.get("dev_otp_code")), f"Code: {body2.get('dev_otp_code')}")
        fresh_otp = body2.get("dev_otp_code")

        # TEST 3: Resend OTP Endpoint
        print("\n--- Phase 3: OTP Resend & Cooldown Endpoint ---")
        resp_resend = client.post("/auth/resend-otp", json={"email": test_email})
        check("Resend OTP returns 200 OK", resp_resend.status_code == 200, f"Status: {resp_resend.status_code}")
        resend_body = resp_resend.json()
        check("Resend OTP provides active code", bool(resend_body.get("dev_otp_code")), f"Resend Code: {resend_body.get('dev_otp_code')}")
        active_otp = resend_body.get("dev_otp_code")

        # TEST 4: Invalid OTP Verification Check
        print("\n--- Phase 4: OTP Verification Logic & Rate Limiting ---")
        resp_bad_otp = client.post("/auth/verify-otp", json={"email": test_email, "otp": "000000"})
        check("Invalid OTP returns 400 Bad Request", resp_bad_otp.status_code == 400, f"Status: {resp_bad_otp.status_code}")
        check("Invalid OTP message mentions verification failure", "invalid" in resp_bad_otp.json().get("detail", "").lower() or "incorrect" in resp_bad_otp.json().get("detail", "").lower(), f"Detail: {resp_bad_otp.json().get('detail')}")

        # TEST 5: Successful OTP Verification
        resp_good_otp = client.post("/auth/verify-otp", json={"email": test_email, "otp": active_otp})
        check("Valid OTP verification returns 200 OK", resp_good_otp.status_code == 200, f"Status: {resp_good_otp.status_code}")
        good_otp_body = resp_good_otp.json()
        check("Email verification confirmed in response", good_otp_body.get("email_verified") is True)
        check("Doctor status remains PENDING for admin review", good_otp_body.get("verification_status") == "PENDING")

        # Verify in DB
        db.expire_all()
        doc_in_db = db.query(Doctor).filter(Doctor.email == test_email).first()
        check("Database confirms doctor email_verified == True", doc_in_db.email_verified is True)
        check("Database confirms verification_status == 'PENDING'", doc_in_db.verification_status == "PENDING")

        # TEST 6: Duplicate Registration After Verification Rejection
        print("\n--- Phase 5: Verified Duplicate Rejection ---")
        resp_dup = client.post("/auth/register", data=reg_payload)
        check("Duplicate registration of VERIFIED account is properly rejected with 400", resp_dup.status_code == 400, f"Status: {resp_dup.status_code}")
        check("Duplicate error states account already exists and is verified", "already exists" in resp_dup.json().get("detail", "").lower(), f"Detail: {resp_dup.json().get('detail')}")

        # TEST 7: Input Validation Assertions
        print("\n--- Phase 6: Field Validation Tests ---")
        # 7a: Password without uppercase
        resp_pwd_no_upper = client.post("/auth/register", data={
            **reg_payload,
            "email": "unique1@hospital.org",
            "registration_number": "UNIQUE-REG-01",
            "password": "password123!",
            "confirm_password": "password123!",
        })
        check("Password without uppercase rejected with 400", resp_pwd_no_upper.status_code == 400)
        check("Password error specifies uppercase requirement", "uppercase" in resp_pwd_no_upper.json().get("detail", "").lower(), f"Detail: {resp_pwd_no_upper.json().get('detail')}")

        # 7b: Password mismatch
        resp_mismatch = client.post("/auth/register", data={
            **reg_payload,
            "email": "unique2@hospital.org",
            "registration_number": "UNIQUE-REG-02",
            "password": "Password123!",
            "confirm_password": "DifferentPassword123!",
        })
        check("Password mismatch rejected with 400", resp_mismatch.status_code == 400)
        check("Error specifies passwords do not match", "do not match" in resp_mismatch.json().get("detail", "").lower(), f"Detail: {resp_mismatch.json().get('detail')}")

        # 7c: Invalid email format
        resp_bad_email = client.post("/auth/register", data={
            **reg_payload,
            "email": "not-an-email",
            "registration_number": "UNIQUE-REG-03",
        })
        check("Malformed email rejected with 400", resp_bad_email.status_code == 400)

        # TEST 8: Registration with PDF Document Upload
        print("\n--- Phase 7: Document Upload Verification ---")
        pdf_bytes = b"%PDF-1.4 simulated medical license verification document content"
        resp_pdf = client.post(
            "/auth/register",
            data={
                **reg_payload,
                "email": "dr.pdf_candidate@hospital.org",
                "registration_number": "MED-PDF-9921",
            },
            files={"document": ("license_cert.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
        )
        check("Registration with PDF upload returns 201 Created", resp_pdf.status_code == 201, f"Status: {resp_pdf.status_code}")
        check("Response confirms document was uploaded", resp_pdf.json().get("doctor", {}).get("document_uploaded") is True)

        # Clean up PDF candidate
        pdf_doc = db.query(Doctor).filter(Doctor.email == "dr.pdf_candidate@hospital.org").first()
        if pdf_doc:
            db.query(EmailOTP).filter(EmailOTP.doctor_id == pdf_doc.doctor_id).delete()
            db.delete(pdf_doc)
            db.commit()

        # TEST 9: Admin Workflow & Approval
        print("\n--- Phase 8: Admin Queue & Doctor Credential Approval ---")
        # 9a: Login as Administrator
        admin_login_resp = client.post("/auth/login", json={
            "email": "debashish.g333@gmail.com",
            "password": "admin_debashish123",
        })
        check("Admin login returns 200 OK", admin_login_resp.status_code == 200, f"Status: {admin_login_resp.status_code}")
        admin_token = admin_login_resp.json().get("access_token")
        check("Admin token received", bool(admin_token))

        # 9b: Check Debashish Giri is in pending doctors list
        headers = {"Authorization": f"Bearer {admin_token}"}
        pending_resp = client.get("/admin/doctors/pending", headers=headers)
        check("Admin pending doctors query returns 200", pending_resp.status_code == 200)
        raw_pending = pending_resp.json()
        pending_list = raw_pending.get("doctors", []) if isinstance(raw_pending, dict) else raw_pending
        is_in_pending = any(d.get("email") == test_email for d in pending_list)
        check("Verified physician appears in Admin pending queue", is_in_pending)

        # 9c: Admin approves Debashish Giri
        approve_resp = client.patch(
            f"/admin/doctors/{doc_in_db.doctor_id}/approve",
            headers=headers,
        )
        check("Admin approval returns 200 OK", approve_resp.status_code == 200, f"Status: {approve_resp.status_code}")
        check("Approved status reflected in response", approve_resp.json().get("verification_status") == "APPROVED")

        # TEST 10: Doctor Login with Physician Password
        print("\n--- Phase 9: Physician Portal Login with Registered Password ---")
        doc_login_resp = client.post("/auth/login", json={
            "email": test_email,
            "password": "Password123!",
        })
        check("Doctor login returns 200 OK with physician password", doc_login_resp.status_code == 200, f"Status: {doc_login_resp.status_code}")
        doc_login_body = doc_login_resp.json()
        check("Doctor role returned", doc_login_body.get("role") == "DOCTOR", f"Role: {doc_login_body.get('role')}")
        check("Doctor access token issued", bool(doc_login_body.get("access_token")))
        check("Doctor full_name matches", doc_login_body.get("doctor", {}).get("full_name") == "DEBASHISH GIRI")

        # TEST 11: Demo Doctor Login Preserved
        print("\n--- Phase 10: Existing Demo Doctor Login Verification ---")
        demo_resp = client.post("/auth/login", json={
            "email": "dr.carter@hospital.org",
            "password": "demo-doctor-2026",
        })
        check("Demo doctor login (dr.carter@hospital.org) returns 200 OK", demo_resp.status_code == 200)
        check("Demo doctor role is DOCTOR", demo_resp.json().get("role") == "DOCTOR")

    finally:
        # Step 11: Clean up test artifacts so user is free to register in live UI without collision
        try:
            cleanup_docs = db.query(Doctor).filter(
                (Doctor.email == test_email) | (Doctor.registration_number == test_reg_num)
            ).all()
            for cd in cleanup_docs:
                db.query(EmailOTP).filter(EmailOTP.doctor_id == cd.doctor_id).delete()
                db.delete(cd)
            db.commit()
        except Exception as _clean_err:
            print(f"Warning: Cleanup notice: {_clean_err}")
        db.close()

    print("\n" + "=" * 70)
    print(f"AUDIT SUMMARY: {passed} / {total} TESTS PASSED ({100 * passed / total:.1f}%)")
    print("=" * 70)
    return passed == total

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
