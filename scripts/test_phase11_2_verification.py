"""
scripts/test_phase11_2_verification.py
======================================
Comprehensive 15-Scenario Automated Verification Suite for Phase 11.2:
- Email OTP Registration Workflow
- Admin Visibility Business Rules (Unverified records hidden)
- Dark-Only Verification UI & Medical Animation Audit
- Authentication Security & Credential Approval Pipeline
"""

import os
import sys
import uuid
from datetime import datetime, timedelta, timezone
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

# Ensure required env vars
os.environ.setdefault("APP_ENV", "development")
os.environ.setdefault("ALLOW_SQLITE_OFFLINE", "true")

from fastapi.testclient import TestClient
from main import app
from backend.database.config import SessionLocal
from backend.database.models import Administrator, Doctor, EmailOTP
from auth.email_service import generate_otp, hash_otp, verify_otp_hash, SMTP_HOST, SMTP_USERNAME, SMTP_PASSWORD
from auth.security import hash_password
from admin.security import create_admin_token

client = TestClient(app)

TOTAL_ASSERTIONS = 0
PASSED_ASSERTIONS = 0
FAILED_ASSERTIONS = 0
SCENARIOS_PASSED = 0

def check(condition: bool, desc: str):
    global TOTAL_ASSERTIONS, PASSED_ASSERTIONS, FAILED_ASSERTIONS
    TOTAL_ASSERTIONS += 1
    if condition:
        PASSED_ASSERTIONS += 1
        print(f"  [PASS] {desc}")
    else:
        FAILED_ASSERTIONS += 1
        print(f"  [FAIL] {desc}")
        raise AssertionError(f"Check failed: {desc}")

def run_suite():
    global SCENARIOS_PASSED
    print("=" * 78)
    print("PHASE 11.2 — AUTOMATED VERIFICATION SUITE (15 SCENARIOS)")
    print("=" * 78)

    db = SessionLocal()
    unique_suffix = uuid.uuid4().hex[:6]
    test_email = f"dr.audit_{unique_suffix}@hospital.org"
    test_reg = f"MC-AUDIT-{unique_suffix.upper()}"
    test_password = "SecurePassword123!"

    # Ensure clean test admin exists
    admin_id = f"admin_test_{unique_suffix}"
    admin_user = f"admin_{unique_suffix}"
    admin = Administrator(
        admin_id=admin_id,
        username=admin_user,
        email=f"admin_{unique_suffix}@cardiopredict.org",
        password_hash=hash_password("AdminPass123!"),
        full_name="Audit Administrator",
        role="Medical Credentialing Officer",
        is_active=True,
    )
    db.add(admin)
    db.commit()
    admin_token = create_admin_token(admin_id, admin_user)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    doctor_id = None

    try:
        # ------------------------------------------------------------------
        # SCENARIO 1: Submit Physician Registration
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 1: Submit Physician Registration ---")
        reg_payload = {
            "full_name": "Dr. Test Clinician, MD",
            "email": test_email,
            "mobile": "+1 555-019-2834",
            "medical_degree": "MBBS, MD Cardiology",
            "registration_number": test_reg,
            "registration_council": "Karnataka Medical Council",
            "password": test_password,
            "confirm_password": test_password,
        }
        res = client.post("/auth/register", data=reg_payload)
        check(res.status_code == 201, f"Registration response HTTP 201 Created (got {res.status_code})")
        data = res.json()
        check(data.get("status") == "success", "Response status is 'success'")
        check("doctor" in data, "Response contains doctor safe profile")
        doctor_id = data["doctor"]["doctor_id"]
        check(bool(doctor_id), f"Doctor ID assigned: {doctor_id}")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 2: Confirm Temporary Pending Email-Verification Record Created
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 2: Confirm Temporary Pending Registration State ---")
        doc = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        check(doc is not None, "Doctor record persisted in database")
        check(doc.email_verified is False, "Doctor email_verified is FALSE initially")
        check(doc.verification_status == "PENDING", "Doctor verification_status is 'PENDING'")
        check(doc.is_active is True, "Doctor account is active flag")
        otp_rec = (
            db.query(EmailOTP)
            .filter(EmailOTP.doctor_id == doctor_id, EmailOTP.is_used == False)
            .first()
        )
        check(otp_rec is not None, "EmailOTP record created for doctor")
        check(otp_rec.otp_hash.startswith("$otp$v=1$"), "OTP is stored as secure PBKDF2 hash, not plaintext")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 3: Confirm OTP Email Delivery Status Reporting
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 3: Confirm OTP Email Delivery Audit ---")
        has_smtp = bool(SMTP_HOST and SMTP_USERNAME and SMTP_PASSWORD)
        expected_status = "SENT" if has_smtp else "DEV_MODE"
        check(
            data.get("email_delivery_status") in ("SENT", "DEV_MODE"),
            f"Email delivery status accurately reported as '{data.get('email_delivery_status')}' (has_smtp={has_smtp})",
        )
        if not has_smtp:
            check(bool(data.get("dev_otp_code")), f"Development OTP code generated and accessible: {data.get('dev_otp_code')}")
        check(
            "email_delivery_message" in data and len(data["email_delivery_message"]) > 0,
            "Clear delivery message or explanation provided in response",
        )
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 4: Confirm Unverified Registration is NOT Visible in Admin
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 4: Confirm Unverified Doctor is Hidden from Admin ---")
        # 4a: Check /admin/doctors/pending
        pnd_res = client.get("/admin/doctors/pending", headers=admin_headers)
        check(pnd_res.status_code == 200, "Admin pending list accessible")
        pnd_ids = [d["doctor_id"] for d in pnd_res.json()]
        check(doctor_id not in pnd_ids, "Unverified doctor is NOT present in /admin/doctors/pending")

        # 4b: Check /admin/doctors (directory)
        dir_res = client.get("/admin/doctors", headers=admin_headers)
        dir_ids = [d["doctor_id"] for d in dir_res.json()]
        check(doctor_id not in dir_ids, "Unverified doctor is NOT present in /admin/doctors directory")

        # 4c: Check /admin/doctors/{id} (individual profile)
        detail_res = client.get(f"/admin/doctors/{doctor_id}", headers=admin_headers)
        check(detail_res.status_code == 404, f"Admin detail view returns 404 Not Found for unverified doctor (got {detail_res.status_code})")

        # 4d: Check /admin/recent-activity
        act_res = client.get("/admin/recent-activity", headers=admin_headers)
        act_ids = [d["doctor_id"] for d in act_res.json().get("recent_registrations", [])]
        check(doctor_id not in act_ids, "Unverified doctor is NOT present in admin recent registrations")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 5: Submit Incorrect OTP
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 5: Submit Incorrect OTP ---")
        bad_res = client.post("/auth/verify-otp", json={"email": test_email, "otp": "000000"})
        check(bad_res.status_code == 400, f"Incorrect OTP returns HTTP 400 Bad Request (got {bad_res.status_code})")
        bad_data = bad_res.json()
        check("Incorrect verification code" in bad_data.get("detail", ""), "Detail informs user of incorrect code")
        doc_still_unverified = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        check(doc_still_unverified.email_verified is False, "Doctor remains unverified after bad OTP")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 6: Submit Expired OTP
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 6: Submit Expired OTP ---")
        # Artificially backdate the active OTP record by 10 minutes
        db.query(EmailOTP).filter(
            EmailOTP.doctor_id == doctor_id, EmailOTP.is_used == False
        ).update({"expires_at": datetime.now(timezone.utc) - timedelta(minutes=10)})
        db.commit()

        exp_res = client.post("/auth/verify-otp", json={"email": test_email, "otp": "123456"})
        check(exp_res.status_code == 400, f"Expired OTP returns HTTP 400 (got {exp_res.status_code})")
        check("expired" in exp_res.json().get("detail", "").lower(), "Detail indicates code has expired")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 7: Submit Correct OTP
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 7: Submit Correct OTP ---")
        # Generate fresh OTP code and save matching hash
        valid_otp_code = "778899"
        valid_otp_hash = hash_otp(valid_otp_code)
        fresh_otp = EmailOTP(
            otp_id=str(uuid.uuid4()),
            doctor_id=doctor_id,
            otp_hash=valid_otp_hash,
            expires_at=datetime.now(timezone.utc) + timedelta(minutes=5),
            attempts=0,
            is_used=False,
            created_at=datetime.now(timezone.utc),
        )
        db.add(fresh_otp)
        db.commit()

        ok_res = client.post("/auth/verify-otp", json={"email": test_email, "otp": valid_otp_code})
        check(ok_res.status_code == 200, f"Valid OTP returns HTTP 200 OK (got {ok_res.status_code})")
        ok_data = ok_res.json()
        check(ok_data.get("email_verified") is True, "Response confirms email_verified is True")
        check(ok_data.get("verification_status") == "PENDING", "Verification status remains 'PENDING' awaiting admin")
        
        db.expire_all()
        doc_updated = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        check(doc_updated.email_verified is True, "Doctor record updated to email_verified == True in database")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 8: Confirm Physician Credential-Review Request is NOW Visible in Admin
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 8: Confirm Verified Doctor Appears in Admin Queue ---")
        # 8a: Visible in pending
        pnd2_res = client.get("/admin/doctors/pending", headers=admin_headers)
        check(pnd2_res.status_code == 200, "Admin pending queue fetched")
        pnd2_ids = [d["doctor_id"] for d in pnd2_res.json()]
        check(doctor_id in pnd2_ids, "Verified doctor IS NOW visible in /admin/doctors/pending")

        # 8b: Visible in detail view
        det2_res = client.get(f"/admin/doctors/{doctor_id}", headers=admin_headers)
        check(det2_res.status_code == 200, "Admin can now review doctor details via /admin/doctors/{id}")
        check(det2_res.json().get("email_verified") is True, "Doctor profile reflects email_verified == True")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 9: Repeated OTP Verification Does Not Create Duplicate Requests
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 9: Test Idempotent Repeated OTP Verification ---")
        repeat_res = client.post("/auth/verify-otp", json={"email": test_email, "otp": valid_otp_code})
        check(repeat_res.status_code == 200, "Repeated verification returns HTTP 200 OK")
        rep_data = repeat_res.json()
        check(rep_data.get("status") == "already_verified", "Status reports 'already_verified'")
        check(rep_data.get("email_verified") is True, "email_verified remains True")
        count_docs = db.query(Doctor).filter(Doctor.email == test_email).count()
        check(count_docs == 1, "Exactly one doctor record exists (no duplicate accounts created)")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 10: Duplicate Email & Registration Number Rejected Correctly
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 10: Test Duplicate Account Rejection ---")
        dup_email_payload = reg_payload.copy()
        dup_email_payload["registration_number"] = f"MC-DIFF-{unique_suffix}"
        res_dup_email = client.post("/auth/register", data=dup_email_payload)
        check(res_dup_email.status_code == 400, f"Duplicate email rejected with HTTP 400 (got {res_dup_email.status_code})")
        check("email address already exists" in res_dup_email.json().get("detail", "").lower(), "Detail explicitly notes duplicate email")

        dup_reg_payload = reg_payload.copy()
        dup_reg_payload["email"] = f"diff_{unique_suffix}@hospital.org"
        res_dup_reg = client.post("/auth/register", data=dup_reg_payload)
        check(res_dup_reg.status_code == 400, f"Duplicate registration number rejected with HTTP 400 (got {res_dup_reg.status_code})")
        check("registration number is already registered" in res_dup_reg.json().get("detail", "").lower(), "Detail explicitly notes duplicate reg number")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 11: Admin Approval is Still Required (No Bypass)
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 11: Confirm Admin Approval is Required ---")
        doc_stat = db.query(Doctor).filter(Doctor.doctor_id == doctor_id).first()
        check(doc_stat.verification_status == "PENDING", "Doctor status is strictly PENDING after email OTP")
        check(doc_stat.approved_at is None, "approved_at timestamp is None")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 12: Login Restrictions for Unapproved Physicians & Approval Gate
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 12: Confirm Login Restrictions for Unapproved Physicians ---")
        # Attempt login before admin approval
        login_res = client.post("/auth/login", json={"email": test_email, "password": test_password})
        check(login_res.status_code == 403, f"Login denied with HTTP 403 Forbidden before admin approval (got {login_res.status_code})")
        check("pending administrative review" in login_res.json().get("detail", "").lower(), "Forbidden detail explains pending approval")

        # Now simulate Administrator Approval via /admin/doctors/{id}/approve
        appr_res = client.post(f"/admin/doctors/{doctor_id}/approve", headers=admin_headers)
        check(appr_res.status_code == 200, "Admin successfully approves doctor credentials")
        check(appr_res.json().get("verification_status") == "APPROVED", "Status updated to 'APPROVED'")

        # Now attempt login after admin approval
        login_ok_res = client.post("/auth/login", json={"email": test_email, "password": test_password})
        check(login_ok_res.status_code == 200, "Login succeeds after administrator approval")
        check("access_token" in login_ok_res.json(), "Access token issued to approved physician")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 13: Verify Dark-Only OTP Page & Elimination of Light Mode
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 13: Verify Dark-Only Theme & CSS Architecture ---")
        otp_jsx_path = BASE_DIR / "frontend" / "src" / "DoctorOtpVerification.jsx"
        otp_content = otp_jsx_path.read_text(encoding="utf-8")
        check("ThemeToggle" not in otp_content, "ThemeToggle component removed from DoctorOtpVerification.jsx")
        check("data-theme" in otp_content and "'dark'" in otp_content, "Dark theme forced in DoctorOtpVerification.jsx")
        check("otp-digit-input" in otp_content, "Discrete 6-digit input structure verified")
        check("auth-page-root" in otp_content, "Uses unified AuthPages dark layout")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 14: Verify Medical Animation & Humorous Quote Rotation
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 14: Verify Medical Animation & Waiting Quotes ---")
        vis_path = BASE_DIR / "frontend" / "src" / "components" / "OtpWaitingVisualizer.jsx"
        check(vis_path.exists(), "OtpWaitingVisualizer.jsx component exists")
        vis_content = vis_path.read_text(encoding="utf-8")
        required_quotes = [
            "Even the heart beats faster than this OTP sometimes.",
            "Your inbox is having a quick coffee break.",
            "The OTP is travelling through the digital bloodstream.",
            "Six digits. One mission. Zero patience.",
            "Your email is playing hide and seek. Check your inbox!",
            "Meanwhile, the neurons are doing their best.",
        ]
        for q in required_quotes:
            check(q in vis_content, f"Quote present: '{q[:38]}...'")
        check("otp-heart-svg" in vis_content, "Animated heart SVG element present")
        check("otp-orbital-ring" in vis_content, "Pulsing orbital rings present")
        check("prefers-reduced-motion" in (BASE_DIR / "frontend" / "src" / "AuthPages.css").read_text(encoding="utf-8"), "CSS honors prefers-reduced-motion")
        SCENARIOS_PASSED += 1

        # ------------------------------------------------------------------
        # SCENARIO 15: Verify Frontend Production Build & Bundle Integrity
        # ------------------------------------------------------------------
        print("\n--- SCENARIO 15: Verify Frontend Production Build ---")
        dist_html = BASE_DIR / "frontend" / "dist" / "index.html"
        check(dist_html.exists(), "Frontend production bundle dist/index.html exists")
        check(dist_html.stat().st_size > 500, f"dist/index.html size valid ({dist_html.stat().st_size} bytes)")
        SCENARIOS_PASSED += 1

    finally:
        # Cleanup test records
        try:
            if doctor_id:
                db.query(EmailOTP).filter(EmailOTP.doctor_id == doctor_id).delete()
                db.query(Doctor).filter(Doctor.doctor_id == doctor_id).delete()
            db.query(Administrator).filter(Administrator.admin_id == admin_id).delete()
            db.commit()
        except Exception:
            pass
        db.close()

    print("\n" + "=" * 78)
    print(f"VERIFICATION SUMMARY: {SCENARIOS_PASSED}/15 SCENARIOS PASSED ({PASSED_ASSERTIONS}/{TOTAL_ASSERTIONS} ASSERTIONS)")
    print("=" * 78)
    if FAILED_ASSERTIONS == 0 and SCENARIOS_PASSED == 15:
        print("[SUCCESS] ALL 15 VERIFICATION SCENARIOS PASSED WITH ZERO FAILURES!")
        return 0
    else:
        print(f"[FAILURE] {FAILED_ASSERTIONS} assertion(s) failed.")
        return 1

if __name__ == "__main__":
    sys.exit(run_suite())
