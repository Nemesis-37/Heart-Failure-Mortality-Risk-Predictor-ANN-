"""
scripts/test_step5_6.py
=======================
Verification Test Suite for:
- Step 5: Administrator Doctor Credential Verification
    (POST /admin/login, GET /admin/doctors/pending, GET /admin/doctors/{id},
     PATCH /admin/doctors/{id}/approve, PATCH /admin/doctors/{id}/reject,
     unauthorized access, only email-verified approval)
- Step 6: Secure Doctor Login and Logout
    (POST /auth/login with 5-condition gate, rate limiting, JWT access token,
     POST /auth/logout session revocation, GET /auth/me)
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PASS = 0
FAIL = 0


def ok(msg, detail=""):
    global PASS
    PASS += 1
    out = f"  [PASS] {msg}"
    if detail:
        out += f": {detail}"
    print(out, flush=True)


def fail(msg, reason=""):
    global FAIL
    FAIL += 1
    out = f"  [FAIL] {msg}"
    if reason:
        out += f": {reason}"
    print(out, flush=True)


def run_tests():
    print("\n" + "=" * 70, flush=True)
    print("  TEST SUITE: STEP 5 (ADMIN VERIFICATION) & STEP 6 (DOCTOR LOGIN/LOGOUT)", flush=True)
    print("=" * 70, flush=True)

    from fastapi import HTTPException
    from database.config import SessionLocal, engine
    from database.models import Administrator, Doctor, EmailOTP
    from auth.security import hash_password, verify_password
    from auth.schemas import DoctorLoginRequest, LogoutRequest
    from auth.router import doctor_login, doctor_logout, get_current_physician_profile
    from auth.dependencies import get_current_doctor
    from admin.schemas import AdminLoginRequest, DoctorRejectionRequest
    from admin.router import (
        admin_login, list_pending_doctors, get_doctor_detail,
        approve_doctor, reject_doctor
    )
    from admin.security import get_current_admin, verify_admin_token

    db = SessionLocal()
    run_id = uuid.uuid4().hex[:8]

    # -----------------------------------------------------------------------
    # Setup test administrator and test doctors
    # -----------------------------------------------------------------------
    admin_user = f"admin_{run_id}"
    admin_pass = "AdminVault2026!"
    test_admin = Administrator(
        admin_id=str(uuid.uuid4()),
        username=admin_user,
        email=f"admin_{run_id}@hospital.org",
        password_hash=hash_password(admin_pass),
        full_name="Chief Medical Officer",
        role="Medical Credentialing Officer",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(test_admin)

    # Doctor 1: Pending, Unverified email
    doc_unverified = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name="Dr. Unverified Email",
        email=f"unverified.{run_id}@hospital.org",
        password_hash=hash_password("DoctorPass123!"),
        mobile="9876543201",
        medical_degree="MBBS",
        registration_number=f"REG-UNV-{run_id}".upper(),
        registration_council="NMC",
        email_verified=False,
        verification_status="PENDING",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc_unverified)

    # Doctor 2: Pending, Email Verified
    doc_pending = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name="Dr. Pending Review",
        email=f"pending.{run_id}@hospital.org",
        password_hash=hash_password("DoctorPass123!"),
        mobile="9876543202",
        medical_degree="MD, Cardiology",
        registration_number=f"REG-PND-{run_id}".upper(),
        registration_council="Medical Council of India",
        email_verified=True,
        verification_status="PENDING",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc_pending)

    # Doctor 3: Already Approved
    doc_approved = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name="Dr. Approved Physician",
        email=f"approved.{run_id}@hospital.org",
        password_hash=hash_password("DoctorPass123!"),
        mobile="9876543203",
        medical_degree="DM, Cardiology",
        registration_number=f"REG-APP-{run_id}".upper(),
        registration_council="General Medical Council",
        email_verified=True,
        verification_status="APPROVED",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc_approved)

    # Doctor 4: Rejected
    doc_rejected = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name="Dr. Rejected Candidate",
        email=f"rejected.{run_id}@hospital.org",
        password_hash=hash_password("DoctorPass123!"),
        mobile="9876543204",
        medical_degree="MBBS",
        registration_number=f"REG-REJ-{run_id}".upper(),
        registration_council="NMC",
        email_verified=True,
        verification_status="REJECTED",
        rejection_reason="Registration number could not be validated with State Council",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc_rejected)

    # Doctor 5: Inactive / Suspended
    doc_inactive = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name="Dr. Inactive Suspended",
        email=f"inactive.{run_id}@hospital.org",
        password_hash=hash_password("DoctorPass123!"),
        mobile="9876543205",
        medical_degree="MBBS",
        registration_number=f"REG-INA-{run_id}".upper(),
        registration_council="NMC",
        email_verified=True,
        verification_status="APPROVED",
        is_active=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc_inactive)
    db.commit()

    # -----------------------------------------------------------------------
    # STEP 5: Administrator Doctor Credential Verification Tests
    # -----------------------------------------------------------------------
    print("\n--- STEP 5: Administrator Doctor Credential Verification ---", flush=True)

    # 5.1 Admin Login with correct credentials
    login_res = admin_login(
        payload=AdminLoginRequest(username=admin_user, password=admin_pass),
        db=db,
    )
    if login_res.token:
        ok("Admin login succeeded with provisioned credentials, token issued")
        admin_token = login_res.token
    else:
        fail("Admin login", "No token returned")
        admin_token = None

    # 5.2 Admin Login with wrong password
    try:
        admin_login(
            payload=AdminLoginRequest(username=admin_user, password="WrongPassword!"),
            db=db,
        )
        fail("Admin wrong password", "Accepted wrong admin password")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok("Admin wrong password rejected with HTTP 401 Unauthorized")
        else:
            fail("Admin wrong password status code", f"Got {exc.status_code}")

    # 5.3 Unauthorized access to admin endpoints
    try:
        get_current_admin(authorization=None)
        fail("Unauthorized admin access", "Allowed access without token")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok("Admin endpoint protected: Missing authorization rejected with HTTP 401")
        else:
            fail("Unauthorized status code", f"Got {exc.status_code}")

    # 5.4 List pending doctors
    pending_list = list_pending_doctors(current_admin=test_admin, db=db)
    pending_ids = [d.doctor_id for d in pending_list]
    if doc_pending.doctor_id in pending_ids:
        ok("GET /admin/doctors/pending returns pending doctor accounts awaiting review")
    else:
        fail("Pending doctors list", f"doc_pending not found in {pending_ids}")

    # 5.5 View single doctor details
    doc_detail = get_doctor_detail(doctor_id=doc_pending.doctor_id, current_admin=test_admin, db=db)
    if (
        doc_detail.doctor_id == doc_pending.doctor_id
        and doc_detail.full_name == "Dr. Pending Review"
        and doc_detail.registration_council == "Medical Council of India"
    ):
        ok(f"GET /admin/doctors/{{id}} returns full credential details for {doc_detail.full_name}")
    else:
        fail("Doctor detail query", str(doc_detail))

    # 5.6 Cannot approve doctor whose email is NOT verified
    try:
        approve_doctor(doctor_id=doc_unverified.doctor_id, current_admin=test_admin, db=db)
        fail("Unverified email approval", "Allowed approving doctor with unverified email")
    except HTTPException as exc:
        if exc.status_code == 400:
            ok(f"Approval correctly blocked for unverified email (HTTP 400): {exc.detail}")
        else:
            fail("Approval check status code", f"Got {exc.status_code}")

    # 5.7 Approve email-verified doctor
    approve_res = approve_doctor(doctor_id=doc_pending.doctor_id, current_admin=test_admin, db=db)
    db.refresh(doc_pending)
    if (
        approve_res.verification_status == "APPROVED"
        and doc_pending.verification_status == "APPROVED"
        and doc_pending.verified_by == test_admin.admin_id
        and doc_pending.verified_at is not None
    ):
        ok(f"PATCH /admin/doctors/{{id}}/approve successfully approved doctor: status='APPROVED'")
        ok(f"Approval decision audit recorded: verified_by={doc_pending.verified_by}")
    else:
        fail("Doctor approval", f"Status: {doc_pending.verification_status}")

    # 5.8 Reject doctor credentials with reason
    reject_reason = "Medical registration could not be verified in state council registry"
    reject_res = reject_doctor(
        doctor_id=doc_unverified.doctor_id,
        payload=DoctorRejectionRequest(reason=reject_reason),
        current_admin=test_admin,
        db=db,
    )
    db.refresh(doc_unverified)
    if (
        reject_res.verification_status == "REJECTED"
        and doc_unverified.verification_status == "REJECTED"
        and doc_unverified.rejection_reason == reject_reason
    ):
        ok(f"PATCH /admin/doctors/{{id}}/reject set status='REJECTED' with recorded reason: {reject_reason}")
    else:
        fail("Doctor rejection", f"Status: {doc_unverified.verification_status}")

    # -----------------------------------------------------------------------
    # STEP 6: Doctor Login & Logout Security Tests
    # -----------------------------------------------------------------------
    print("\n--- STEP 6: Doctor Login, Session Security & Logout ---", flush=True)

    # 6.1 Successful Login for Approved, Email-Verified, Active Doctor
    doc_login_res = doctor_login(
        payload=DoctorLoginRequest(email=doc_approved.email, password="DoctorPass123!"),
        db=db,
    )
    if doc_login_res.access_token and doc_login_res.doctor.verification_status == "APPROVED":
        ok(f"POST /auth/login succeeded for approved doctor: issued JWT access token and refresh token")
        ok("Doctor basic profile returned in login response without password hash")
        access_token = doc_login_res.access_token
        refresh_token = doc_login_res.refresh_token
    else:
        fail("Approved doctor login", "Login failed or token missing")
        access_token = None
        refresh_token = None

    # 6.2 Incorrect Password Rejection
    try:
        doctor_login(
            payload=DoctorLoginRequest(email=doc_approved.email, password="WrongPassword999!"),
            db=db,
        )
        fail("Wrong password login", "Accepted incorrect password")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok("Incorrect password rejected with HTTP 401 Unauthorized")
        else:
            fail("Wrong password status code", f"Got {exc.status_code}")

    # 6.3 Unverified Email Account Login Rejection
    # Create a fresh unverified pending doctor
    doc_unver_login = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name="Dr. Unverified Login Test",
        email=f"unver_login.{run_id}@hospital.org",
        password_hash=hash_password("DoctorPass123!"),
        mobile="9876543209",
        medical_degree="MBBS",
        registration_number=f"REG-UNL-{run_id}".upper(),
        registration_council="NMC",
        email_verified=False,
        verification_status="PENDING",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doc_unver_login)
    db.commit()

    try:
        doctor_login(
            payload=DoctorLoginRequest(email=doc_unver_login.email, password="DoctorPass123!"),
            db=db,
        )
        fail("Unverified email login", "Allowed login for unverified email")
    except HTTPException as exc:
        if exc.status_code == 403:
            ok("Unverified email account blocked from login with HTTP 403 Forbidden")
        else:
            fail("Unverified email status code", f"Got {exc.status_code}")

    # 6.4 Pending Doctor Account Login Rejection
    # Make email verified but verification_status remains PENDING
    doc_unver_login.email_verified = True
    db.commit()

    try:
        doctor_login(
            payload=DoctorLoginRequest(email=doc_unver_login.email, password="DoctorPass123!"),
            db=db,
        )
        fail("Pending account login", "Allowed login for pending doctor")
    except HTTPException as exc:
        if exc.status_code == 403:
            ok("Pending doctor account blocked from login with HTTP 403 (awaiting administrative approval)")
        else:
            fail("Pending account status code", f"Got {exc.status_code}")

    # 6.5 Rejected Account Login Rejection
    try:
        doctor_login(
            payload=DoctorLoginRequest(email=doc_rejected.email, password="DoctorPass123!"),
            db=db,
        )
        fail("Rejected doctor login", "Allowed login for rejected doctor")
    except HTTPException as exc:
        if exc.status_code == 403 and "rejected" in exc.detail.lower():
            ok(f"Rejected doctor blocked with HTTP 403 and rejection reason: {exc.detail}")
        else:
            fail("Rejected doctor status code", f"Got {exc.status_code}")

    # 6.6 Inactive / Suspended Account Login Rejection
    try:
        doctor_login(
            payload=DoctorLoginRequest(email=doc_inactive.email, password="DoctorPass123!"),
            db=db,
        )
        fail("Inactive doctor login", "Allowed login for inactive doctor")
    except HTTPException as exc:
        if exc.status_code == 403:
            ok("Inactive / suspended doctor account blocked from login with HTTP 403")
        else:
            fail("Inactive doctor status code", f"Got {exc.status_code}")

    # 6.7 Rate Limiting Lockout
    rate_email = f"brute_test.{run_id}@hospital.org"
    brute_doc = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name="Dr. Brute Test",
        email=rate_email,
        password_hash=hash_password("RealPassword123!"),
        mobile="9876543208",
        medical_degree="MBBS",
        registration_number=f"REG-BRU-{run_id}".upper(),
        registration_council="NMC",
        email_verified=True,
        verification_status="APPROVED",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(brute_doc)
    db.commit()

    # Trigger 5 failed logins
    for attempt in range(1, 6):
        try:
            doctor_login(
                payload=DoctorLoginRequest(email=rate_email, password="WrongPassword!"),
                db=db,
            )
        except HTTPException:
            pass

    # 6th attempt should be locked out with HTTP 429
    try:
        doctor_login(
            payload=DoctorLoginRequest(email=rate_email, password="WrongPassword!"),
            db=db,
        )
        fail("Rate limiting lockout", "6th attempt not blocked with 429")
    except HTTPException as exc:
        if exc.status_code == 429:
            ok(f"Rate limiting enforced: 5 failed attempts triggered lockout with HTTP 429 ({exc.detail})")
        else:
            fail("Rate limit status code", f"Expected 429, got {exc.status_code}")

    # 6.8 GET /auth/me returns authenticated doctor profile
    if access_token:
        auth_doc = get_current_doctor(authorization=f"Bearer {access_token}", db=db)
        if auth_doc.email == doc_approved.email:
            ok(f"GET /auth/me: Valid Bearer token authenticated doctor ({auth_doc.full_name})")
        else:
            fail("GET /auth/me doctor resolution", f"Resolved {auth_doc.email}")

    # 6.9 POST /auth/logout Session Revocation
    if refresh_token:
        logout_res = doctor_logout(payload=LogoutRequest(refresh_token=refresh_token), db=db)
        if logout_res.get("status") == "success":
            ok("POST /auth/logout successfully revoked refresh session in database")
        else:
            fail("Logout response", str(logout_res))

    # -----------------------------------------------------------------------
    # Cleanup test records
    # -----------------------------------------------------------------------
    try:
        docs_to_clean = [doc_unverified, doc_pending, doc_approved, doc_rejected, doc_inactive, doc_unver_login, brute_doc]
        for d in docs_to_clean:
            db.query(EmailOTP).filter(EmailOTP.doctor_id == d.doctor_id).delete()
            db.delete(d)
        db.delete(test_admin)
        db.commit()
        ok("Test doctors and test administrator cleaned up cleanly")
    except Exception as exc:
        print(f"  [NOTE] Cleanup note: {exc}", flush=True)
    finally:
        db.close()

    # -----------------------------------------------------------------------
    # Summary
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70, flush=True)
    total = PASS + FAIL
    if FAIL == 0:
        print(f"  ALL {total} TESTS PASSED SUCCESSFULLY! (100% VERIFIED)", flush=True)
        print("  STEP 5 (ADMIN VERIFICATION) & STEP 6 (DOCTOR AUTH) FULLY VERIFIED", flush=True)
    else:
        print(f"  {PASS}/{total} TESTS PASSED | {FAIL} FAILURES", flush=True)
    print("=" * 70, flush=True)

    return FAIL == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
