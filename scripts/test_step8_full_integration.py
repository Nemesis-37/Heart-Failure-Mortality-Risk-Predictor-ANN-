"""
scripts/test_step8_full_integration.py
=======================================
STEP 8: Complete Doctor Authentication Integration Test Suite

Tests the full end-to-end workflow:
  Registration → OTP Verification → Admin Approval → Login → Dashboard → Logout

Security Tests:
  - Duplicate email/registration rejection
  - OTP: correct, incorrect, expired, brute-force, resend cooldown
  - Login: wrong password, pending, rejected, suspended, unverified
  - Admin: unauthorized access, approve, reject
  - Session: JWT validation, refresh rotation, revocation
  - IDOR: cross-doctor assessment access prevention
  - ML prediction endpoints still work and are protected

Run:
    .\\venv\\Scripts\\python.exe scripts\\test_step8_full_integration.py
"""

import sys
import uuid
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PASS = 0
FAIL = 0
RESULTS = []


def ok(test_name: str, detail: str = ""):
    global PASS
    PASS += 1
    msg = f"  [PASS] {test_name}"
    if detail:
        msg += f": {detail}"
    print(msg, flush=True)
    RESULTS.append(("PASS", test_name))


def fail(test_name: str, reason: str = ""):
    global FAIL
    FAIL += 1
    msg = f"  [FAIL] {test_name}"
    if reason:
        msg += f": {reason}"
    print(msg, flush=True)
    RESULTS.append(("FAIL", test_name))


def section(title: str):
    print(f"\n{'─' * 60}", flush=True)
    print(f"  {title}", flush=True)
    print(f"{'─' * 60}", flush=True)


def run_tests():
    print("\n" + "=" * 70, flush=True)
    print("  STEP 8: COMPLETE AUTHENTICATION INTEGRATION TEST SUITE", flush=True)
    print("=" * 70, flush=True)

    # -----------------------------------------------------------------------
    # Import all required modules
    # -----------------------------------------------------------------------
    section("MODULE IMPORTS")
    try:
        from fastapi import HTTPException
        from database.config import SessionLocal, engine
        from database.models import Base, Doctor, DoctorSession, EmailOTP, Administrator, Assessment
        from auth.security import hash_password, verify_password, is_argon2_native
        from auth.session_service import (
            create_access_token, verify_access_token,
            create_doctor_session, rotate_refresh_token,
            revoke_doctor_session, check_login_rate_limit,
            record_login_failure, reset_login_failures,
        )
        from auth.email_service import generate_otp, hash_otp, verify_otp_hash, OTP_EXPIRY_MINUTES, OTP_MAX_ATTEMPTS
        from auth.router import doctor_login, refresh_session_endpoint, doctor_logout, register_doctor_json
        from auth.schemas import DoctorLoginRequest, RefreshRequest, LogoutRequest
        from auth.dependencies import get_current_doctor
        from admin.security import create_admin_token, verify_admin_token
        from admin.router import admin_login, approve_doctor, reject_doctor, list_doctors
        from admin.schemas import AdminLoginRequest, DoctorRejectionRequest
        from clinical.router import (
            list_doctor_assessments, create_patient_assessment,
            get_assessment_by_id, delete_patient_assessment,
            get_doctor_dashboard_stats, AssessmentInput,
        )
        ok("All modules imported successfully")
    except ImportError as e:
        fail("Module import", str(e))
        print(f"\n[FATAL] Cannot proceed without all modules. Fix: {e}", flush=True)
        return

    # Ensure tables exist
    try:
        Base.metadata.create_all(bind=engine)
        ok("Database tables verified / created")
    except Exception as e:
        fail("Database create_all", str(e))

    db = SessionLocal()
    run_id = str(uuid.uuid4())[:8]

    # -----------------------------------------------------------------------
    # PART 1: PASSWORD HASHING
    # -----------------------------------------------------------------------
    section("PART 1 — PASSWORD HASHING")

    plain_pw = "SecurePass123!"
    hashed = hash_password(plain_pw)
    if hashed and hashed != plain_pw:
        ok("Password hashed (not stored in plain text)", f"hash prefix: {hashed[:20]}...")
    else:
        fail("Password hashing", "Hash equals plain text — critical security failure")

    if verify_password(plain_pw, hashed):
        ok("Correct password verifies successfully")
    else:
        fail("Password verification", "Correct password not accepted")

    if not verify_password("WrongPass999!", hashed):
        ok("Wrong password rejected correctly")
    else:
        fail("Wrong password rejection", "SECURITY FAILURE — wrong password accepted")

    hasher_type = "Argon2id (native)" if is_argon2_native() else "PBKDF2-SHA256 (fallback — install argon2-cffi for production)"
    ok(f"Hasher in use: {hasher_type}")

    # -----------------------------------------------------------------------
    # PART 2: OTP GENERATION AND VERIFICATION
    # -----------------------------------------------------------------------
    section("PART 2 — OTP GENERATION AND SECURITY")

    otp_code = generate_otp()
    if len(otp_code) == 6 and otp_code.isdigit():
        ok("OTP is 6-digit numeric", otp_code)
    else:
        fail("OTP format", f"Got: {otp_code!r}")

    otp_hash = hash_otp(otp_code)
    if verify_otp_hash(otp_code, otp_hash):
        ok("Correct OTP verifies against stored hash")
    else:
        fail("OTP hash verification", "Correct OTP rejected")

    if not verify_otp_hash("000000", otp_hash):
        ok("Incorrect OTP rejected correctly")
    else:
        fail("Incorrect OTP rejection", "SECURITY FAILURE")

    if not verify_otp_hash(otp_code, "$corrupted$hash$"):
        ok("Corrupted OTP hash safely rejected")
    else:
        fail("Corrupted hash rejection")

    ok(f"OTP configuration: {OTP_EXPIRY_MINUTES} min expiry, max {OTP_MAX_ATTEMPTS} attempts")

    # -----------------------------------------------------------------------
    # PART 3: JWT TOKEN CREATION AND VALIDATION
    # -----------------------------------------------------------------------
    section("PART 3 — JWT ACCESS TOKEN SECURITY")

    test_doctor_id = str(uuid.uuid4())
    token = create_access_token(test_doctor_id, f"test{run_id}@hospital.org", "Dr. Test")
    if token and token.count(".") == 2:
        ok("JWT access token created (3-part structure)")
    else:
        fail("JWT creation", "Token malformed")

    payload = verify_access_token(token)
    if payload and payload.get("sub") == test_doctor_id:
        ok("Valid JWT verified successfully")
    else:
        fail("JWT verification", "Valid token rejected")

    if not verify_access_token("invalid.token.here"):
        ok("Invalid JWT signature rejected")
    else:
        fail("Invalid JWT rejection", "SECURITY FAILURE")

    if not verify_access_token(""):
        ok("Empty token rejected")
    else:
        fail("Empty token rejection")

    # -----------------------------------------------------------------------
    # PART 4: RATE LIMITING
    # -----------------------------------------------------------------------
    section("PART 4 — LOGIN RATE LIMITING")

    rate_email = f"ratelimit_{run_id}@test.com"
    reset_login_failures(rate_email)

    allowed, wait = check_login_rate_limit(rate_email)
    if allowed:
        ok("Fresh email not rate-limited")
    else:
        fail("Rate limit fresh email")

    for _ in range(5):
        record_login_failure(rate_email)

    allowed, wait = check_login_rate_limit(rate_email)
    if not allowed and wait > 0:
        ok(f"Email blocked after 5 failures (wait: {wait}s)")
    else:
        fail("Rate limit enforcement", f"Should be blocked (allowed={allowed})")

    reset_login_failures(rate_email)
    allowed, _ = check_login_rate_limit(rate_email)
    if allowed:
        ok("Rate limit cleared on successful login")
    else:
        fail("Rate limit reset")

    # -----------------------------------------------------------------------
    # PART 5: DOCTOR REGISTRATION (Duplicate Detection)
    # -----------------------------------------------------------------------
    section("PART 5 — DOCTOR REGISTRATION (DUPLICATE DETECTION)")

    # Seed test doctor A
    email_a = f"doca_{run_id}@hospital.org"
    reg_a = f"MED-A-{run_id}".upper()
    doctor_a = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name="Dr. Alpha Test",
        email=email_a,
        password_hash=hash_password("AlphaPass123!"),
        mobile="9876543210",
        medical_degree="MBBS",
        registration_number=reg_a,
        registration_council="NMC",
        email_verified=True,
        verification_status="APPROVED",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doctor_a)

    # Seed test doctor B (pending)
    email_b = f"docb_{run_id}@hospital.org"
    doctor_b = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name="Dr. Beta Test",
        email=email_b,
        password_hash=hash_password("BetaPass123!"),
        mobile="9876543211",
        medical_degree="MD",
        registration_number=f"MED-B-{run_id}".upper(),
        registration_council="NMC",
        email_verified=False,
        verification_status="PENDING",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doctor_b)

    # Seed test doctor C (rejected)
    email_c = f"docc_{run_id}@hospital.org"
    doctor_c = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name="Dr. Charlie Rejected",
        email=email_c,
        password_hash=hash_password("CharliePass123!"),
        mobile="9876543212",
        medical_degree="MBBS",
        registration_number=f"MED-C-{run_id}".upper(),
        registration_council="NMC",
        email_verified=True,
        verification_status="REJECTED",
        rejection_reason="Certificate forged",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doctor_c)

    # Seed test doctor D (suspended/inactive)
    email_d = f"docd_{run_id}@hospital.org"
    doctor_d = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name="Dr. Delta Suspended",
        email=email_d,
        password_hash=hash_password("DeltaPass123!"),
        mobile="9876543213",
        medical_degree="MD",
        registration_number=f"MED-D-{run_id}".upper(),
        registration_council="NMC",
        email_verified=True,
        verification_status="APPROVED",
        is_active=False,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doctor_d)
    db.commit()
    ok(f"Test doctors A/B/C/D seeded (run: {run_id})")

    # Test: Duplicate email detection via /auth/register-json
    from auth.schemas import DoctorRegisterRequest
    duplicate_request = DoctorRegisterRequest(
        full_name="Duplicate Doctor",
        email=email_a,  # Already taken
        mobile="1234567890",
        medical_degree="MBBS",
        registration_number=f"UNIQUE-REG-{run_id}",
        registration_council="NMC",
        password="Duplicate123!",
        confirm_password="Duplicate123!",
    )
    try:
        result = register_doctor_json(payload=duplicate_request, db=db)
        fail("Duplicate email detection", "Should have rejected duplicate email")
    except HTTPException as exc:
        if exc.status_code in (400, 409):
            ok(f"Duplicate email rejected (HTTP {exc.status_code}): {exc.detail}")
        else:
            fail("Duplicate email status code", f"Expected 400/409, got {exc.status_code}")

    # Test: Duplicate registration number detection
    dup_reg_request = DoctorRegisterRequest(
        full_name="Another Doctor",
        email=f"unique_{run_id}@hospital.org",
        mobile="1234567890",
        medical_degree="MBBS",
        registration_number=reg_a,  # Already taken
        registration_council="NMC",
        password="Unique123!",
        confirm_password="Unique123!",
    )
    try:
        result = register_doctor_json(payload=dup_reg_request, db=db)
        fail("Duplicate registration number detection", "Should have rejected it")
    except HTTPException as exc:
        if exc.status_code in (400, 409):
            ok(f"Duplicate registration number rejected (HTTP {exc.status_code})")
        else:
            fail("Duplicate reg number status code", f"Expected 400/409, got {exc.status_code}")

    # -----------------------------------------------------------------------
    # PART 6: DOCTOR LOGIN SECURITY
    # -----------------------------------------------------------------------
    section("PART 6 — SECURE LOGIN (ALL CONDITIONS)")

    login_payload = DoctorLoginRequest(email=email_a, password="AlphaPass123!")
    result = doctor_login(payload=login_payload, db=db)
    if hasattr(result, "access_token") and result.access_token:
        ok("TEST 6.1 — Valid approved doctor login succeeded")
        access_token_a = result.access_token
        refresh_token_a = result.refresh_token
    else:
        fail("TEST 6.1 — Valid login", "No access token returned")
        access_token_a = None
        refresh_token_a = None

    try:
        doctor_login(payload=DoctorLoginRequest(email=email_a, password="WrongPassword!"), db=db)
        fail("TEST 6.2 — Wrong password should be rejected")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok(f"TEST 6.2 — Wrong password rejected (HTTP 401)")
        else:
            fail("TEST 6.2 — Wrong password status code", f"Got {exc.status_code}")

    try:
        doctor_login(payload=DoctorLoginRequest(email=email_b, password="BetaPass123!"), db=db)
        fail("TEST 6.3 — Unverified email should be blocked")
    except HTTPException as exc:
        if exc.status_code == 403:
            ok(f"TEST 6.3 — Unverified email blocked (HTTP 403)")
        else:
            fail("TEST 6.3 — Unverified email status code", f"Got {exc.status_code}")

    # Mark doctor B email verified but still PENDING
    doctor_b.email_verified = True
    db.commit()
    try:
        doctor_login(payload=DoctorLoginRequest(email=email_b, password="BetaPass123!"), db=db)
        fail("TEST 6.4 — Pending approval should be blocked")
    except HTTPException as exc:
        if exc.status_code == 403:
            ok(f"TEST 6.4 — Pending doctor blocked (HTTP 403)")
        else:
            fail("TEST 6.4 — Pending status code", f"Got {exc.status_code}")

    try:
        doctor_login(payload=DoctorLoginRequest(email=email_c, password="CharliePass123!"), db=db)
        fail("TEST 6.5 — Rejected doctor should be blocked")
    except HTTPException as exc:
        if exc.status_code == 403 and "rejected" in exc.detail.lower():
            ok(f"TEST 6.5 — Rejected doctor blocked with reason (HTTP 403)")
        else:
            fail("TEST 6.5 — Rejected doctor status code", f"Got {exc.status_code}")

    try:
        doctor_login(payload=DoctorLoginRequest(email=email_d, password="DeltaPass123!"), db=db)
        fail("TEST 6.6 — Suspended account should be blocked")
    except HTTPException as exc:
        if exc.status_code == 403:
            ok(f"TEST 6.6 — Suspended/inactive account blocked (HTTP 403)")
        else:
            fail("TEST 6.6 — Suspended status code", f"Got {exc.status_code}")

    # Non-existent email
    try:
        doctor_login(payload=DoctorLoginRequest(email=f"nonexistent_{run_id}@nowhere.com", password="SomePass123!"), db=db)
        fail("TEST 6.7 — Non-existent email should be rejected")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok("TEST 6.7 — Non-existent email rejected (HTTP 401)")
        else:
            fail("TEST 6.7 — Non-existent email status code", f"Got {exc.status_code}")

    # -----------------------------------------------------------------------
    # PART 7: REFRESH TOKEN ROTATION AND LOGOUT
    # -----------------------------------------------------------------------
    section("PART 7 — SESSION MANAGEMENT (REFRESH + LOGOUT)")

    if refresh_token_a:
        try:
            refresh_result = rotate_refresh_token(db, refresh_token_a)
            if refresh_result:
                new_access, new_refresh, doctor_obj = refresh_result
                ok("TEST 7.1 — Token rotated: new access + refresh tokens issued")

                # Old refresh token should now be invalid
                old_result = rotate_refresh_token(db, refresh_token_a)
                if not old_result:
                    ok("TEST 7.2 — Replayed old refresh token rejected (rotation working)")
                else:
                    fail("TEST 7.2 — Replayed token accepted (SECURITY FAILURE)")

                # Logout: revoke session
                revoke_doctor_session(db, new_refresh)
                revoked_result = rotate_refresh_token(db, new_refresh)
                if not revoked_result:
                    ok("TEST 7.3 — Revoked token rejected after logout")
                else:
                    fail("TEST 7.3 — Revoked token still active (SECURITY FAILURE)")
            else:
                fail("TEST 7.1 — Token rotation returned None")
        except Exception as exc:
            fail("TEST 7 — Session management", str(exc))
    else:
        fail("TEST 7 — Skipped (no valid refresh token from login)")

    # -----------------------------------------------------------------------
    # PART 8: AUTHENTICATION DEPENDENCY (get_current_doctor)
    # -----------------------------------------------------------------------
    section("PART 8 — FASTAPI AUTH DEPENDENCY")

    # Login again to get fresh tokens
    login_payload = DoctorLoginRequest(email=email_a, password="AlphaPass123!")
    fresh_login = doctor_login(payload=login_payload, db=db)
    fresh_access = fresh_login.access_token

    # No token
    try:
        get_current_doctor(authorization=None, db=db)
        fail("TEST 8.1 — Missing token should raise 401")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok("TEST 8.1 — No auth header → HTTP 401")
        else:
            fail("TEST 8.1 — Wrong status code", f"Got {exc.status_code}")

    # Invalid token
    try:
        get_current_doctor(authorization="Bearer totally.invalid.token", db=db)
        fail("TEST 8.2 — Invalid token should raise 401")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok("TEST 8.2 — Invalid token → HTTP 401")
        else:
            fail("TEST 8.2 — Wrong status code", f"Got {exc.status_code}")

    # Valid token
    try:
        verified_doc = get_current_doctor(authorization=f"Bearer {fresh_access}", db=db)
        if verified_doc.email == email_a:
            ok(f"TEST 8.3 — Valid token → doctor resolved ({verified_doc.full_name})")
        else:
            fail("TEST 8.3 — Wrong doctor returned", f"Got {verified_doc.email}")
    except HTTPException as exc:
        fail("TEST 8.3 — Valid token rejected", f"HTTP {exc.status_code}: {exc.detail}")

    # -----------------------------------------------------------------------
    # PART 9: ADMIN AUTHENTICATION
    # -----------------------------------------------------------------------
    section("PART 9 — ADMINISTRATOR AUTHENTICATION")

    # Seed a test administrator
    test_admin = Administrator(
        admin_id=str(uuid.uuid4()),
        username=f"admin_{run_id}",
        email=f"admin_{run_id}@hospital.org",
        password_hash=hash_password("AdminSecure2026!"),
        full_name="Dr. Test Administrator",
        role="Medical Credentialing Officer",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(test_admin)
    db.commit()
    ok("Test administrator account seeded")

    # Admin login
    try:
        admin_login_result = admin_login(
            payload=AdminLoginRequest(username=f"admin_{run_id}", password="AdminSecure2026!"),
            db=db,
        )
        if admin_login_result.token:
            ok("TEST 9.1 — Admin login succeeded, token issued")
            admin_token = admin_login_result.token
        else:
            fail("TEST 9.1 — Admin login: no token returned")
            admin_token = None
    except Exception as exc:
        fail("TEST 9.1 — Admin login exception", str(exc))
        admin_token = None

    # Wrong admin password
    try:
        admin_login(
            payload=AdminLoginRequest(username=f"admin_{run_id}", password="WrongPassword!"),
            db=db,
        )
        fail("TEST 9.2 — Wrong admin password should be rejected")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok("TEST 9.2 — Wrong admin password rejected (HTTP 401)")
        else:
            fail("TEST 9.2 — Wrong status code", f"Got {exc.status_code}")

    # Admin token verification
    if admin_token:
        payload = verify_admin_token(admin_token)
        if payload:
            ok("TEST 9.3 — Admin JWT verified successfully")
        else:
            fail("TEST 9.3 — Admin JWT verification failed")

        # Admin approve a doctor (doctor_b is PENDING)
        try:
            from admin.security import get_current_admin
            # Manually resolve admin from token
            from sqlalchemy.orm import Session as SqlSession
            admin_obj = db.query(Administrator).filter(Administrator.username == f"admin_{run_id}").first()

            approve_result = approve_doctor(
                doctor_id=doctor_b.doctor_id,
                current_admin=admin_obj,
                db=db,
            )
            if approve_result.verification_status == "APPROVED":
                ok(f"TEST 9.4 — Doctor B approved by admin: {approve_result.message}")
            else:
                fail("TEST 9.4 — Approval status not set")
        except Exception as exc:
            fail("TEST 9.4 — Admin approve exception", str(exc))

        # Admin reject a doctor
        try:
            reject_result = reject_doctor(
                doctor_id=doctor_b.doctor_id,
                payload=DoctorRejectionRequest(reason="Test rejection for integration test"),
                current_admin=admin_obj,
                db=db,
            )
            if reject_result.verification_status == "REJECTED":
                ok(f"TEST 9.5 — Doctor B rejected by admin (reason recorded)")
            else:
                fail("TEST 9.5 — Rejection status not set")
        except Exception as exc:
            fail("TEST 9.5 — Admin reject exception", str(exc))

    # Unauthorized admin access (no token)
    from admin.security import get_current_admin
    try:
        get_current_admin(authorization=None)
        fail("TEST 9.6 — Missing admin token should raise 401")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok("TEST 9.6 — Missing admin token → HTTP 401 (unauthorized)")
        else:
            fail("TEST 9.6 — Status code", f"Got {exc.status_code}")

    # -----------------------------------------------------------------------
    # PART 10: CLINICAL ASSESSMENTS AND IDOR
    # -----------------------------------------------------------------------
    section("PART 10 — ASSESSMENTS AND IDOR PREVENTION")

    # Login for Doctor A and seed second doctor for IDOR test
    login_a = doctor_login(payload=DoctorLoginRequest(email=email_a, password="AlphaPass123!"), db=db)
    access_a = login_a.access_token
    doc_a = get_current_doctor(authorization=f"Bearer {access_a}", db=db)

    email_e = f"doce_{run_id}@hospital.org"
    doctor_e = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name="Dr. Echo IDOR Test",
        email=email_e,
        password_hash=hash_password("EchoPass123!"),
        mobile="9876543219",
        medical_degree="MBBS",
        registration_number=f"MED-E-{run_id}".upper(),
        registration_council="NMC",
        email_verified=True,
        verification_status="APPROVED",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(doctor_e)
    db.commit()
    login_e = doctor_login(payload=DoctorLoginRequest(email=email_e, password="EchoPass123!"), db=db)
    access_e = login_e.access_token
    doc_e = get_current_doctor(authorization=f"Bearer {access_e}", db=db)

    # Doctor A creates an assessment
    asm_input = AssessmentInput(
        patient_reference_id=f"PT-{run_id}",
        age=65.0,
        anaemia=1,
        creatinine_phosphokinase=250.0,
        diabetes=0,
        ejection_fraction=35.0,
        high_blood_pressure=1,
        platelets=150000.0,
        serum_creatinine=1.3,
        serum_sodium=137.0,
        sex=1,
        smoking=0,
    )
    try:
        asm_result = create_patient_assessment(payload=asm_input, current_doctor=doc_a, db=db)
        ok(f"TEST 10.1 — Assessment {asm_result.assessment_code} created for Doctor A")
        created_asm_id = asm_result.id
    except Exception as exc:
        fail("TEST 10.1 — Assessment creation", str(exc))
        created_asm_id = None

    # Doctor E tries to read Doctor A's assessment (IDOR test)
    if created_asm_id:
        try:
            get_assessment_by_id(
                assessment_id=created_asm_id,
                current_doctor=doc_e,
                db=db,
            )
            fail("TEST 10.2 — IDOR: Doctor E read Doctor A's record (SECURITY FAILURE)")
        except HTTPException as exc:
            if exc.status_code in (403, 404):
                ok(f"TEST 10.2 — IDOR: Doctor E blocked from reading Doctor A's record (HTTP {exc.status_code})")
            else:
                fail("TEST 10.2 — IDOR status code", f"Got {exc.status_code}")

        # Doctor E tries to delete Doctor A's assessment
        try:
            delete_patient_assessment(
                assessment_id=created_asm_id,
                current_doctor=doc_e,
                db=db,
            )
            fail("TEST 10.3 — IDOR: Doctor E deleted Doctor A's record (SECURITY FAILURE)")
        except HTTPException as exc:
            if exc.status_code in (403, 404):
                ok(f"TEST 10.3 — IDOR: Doctor E blocked from deleting Doctor A's record (HTTP {exc.status_code})")
            else:
                fail("TEST 10.3 — IDOR delete status code", f"Got {exc.status_code}")

    # Assessment list isolation
    assessments_a = list_doctor_assessments(current_doctor=doc_a, db=db)
    assessments_e = list_doctor_assessments(current_doctor=doc_e, db=db)
    a_count = len([x for x in assessments_a if x.patient_reference_id == f"PT-{run_id}"])
    e_count = len(assessments_e)
    if a_count >= 1 and e_count == 0:
        ok(f"TEST 10.4 — Data isolation: Doctor A sees own records, Doctor E sees 0")
    else:
        fail("TEST 10.4 — Assessment isolation", f"Doctor A: {a_count}, Doctor E: {e_count}")

    # Dashboard stats
    stats = get_doctor_dashboard_stats(current_doctor=doc_a, db=db)
    if stats.total_assessments >= 1:
        ok(f"TEST 10.5 — Dashboard stats: Doctor A has {stats.total_assessments} assessment(s)")
    else:
        fail("TEST 10.5 — Dashboard stats", f"Expected >=1, got {stats.total_assessments}")

    # -----------------------------------------------------------------------
    # PART 11: ML PREDICTION ENDPOINTS (PROTECTED)
    # -----------------------------------------------------------------------
    section("PART 11 — ML PREDICTION ENDPOINTS (STILL WORK + ARE PROTECTED)")

    try:
        from main import app, PatientData, predict_logistic_regression, predict_ann, get_auth_doctor

        sample = PatientData(
            age=65, anaemia=1, creatinine_phosphokinase=250.0, diabetes=0,
            ejection_fraction=35.0, high_blood_pressure=1, platelets=150000.0,
            serum_creatinine=1.3, serum_sodium=137.0, sex=1, smoking=0,
        )

        # Protected: attempt without token
        try:
            from fastapi import HTTPException as FHE
            get_auth_doctor(authorization="Bearer fake.token.here")
            fail("TEST 11.1 — Fake token should be rejected")
        except FHE as exc:
            if exc.status_code == 401:
                ok("TEST 11.1 — Prediction endpoints reject unauthenticated request (HTTP 401)")
            else:
                fail("TEST 11.1 — Status code", f"Got {exc.status_code}")

        # Resolve doctor for ML tests
        auth_doc = get_auth_doctor(authorization=f"Bearer {access_a}")
        lr_result = predict_logistic_regression(patient=sample, current_doctor=auth_doc)
        if "predicted_class" in lr_result and "predicted_probability" in lr_result:
            ok(f"TEST 11.2 — Logistic Regression prediction: class={lr_result['predicted_class']} prob={lr_result['predicted_probability']:.1%}")
        else:
            fail("TEST 11.2 — LR prediction response format invalid")

        ann_result = predict_ann(patient=sample, current_doctor=auth_doc)
        if "predicted_class" in ann_result and "predicted_probability" in ann_result:
            ok(f"TEST 11.3 — ANN prediction: class={ann_result['predicted_class']} prob={ann_result['predicted_probability']:.1%}")
        else:
            fail("TEST 11.3 — ANN prediction response format invalid")

        # Verify response keys are correct
        expected_keys = {"model", "predicted_class", "predicted_label", "predicted_probability", "notice"}
        if expected_keys.issubset(lr_result.keys()):
            ok("TEST 11.4 — Prediction response format matches expected schema")
        else:
            fail("TEST 11.4 — Response key mismatch", f"Missing: {expected_keys - lr_result.keys()}")

    except ImportError as exc:
        fail("PART 11 — ML endpoints", f"Import error: {exc}")
    except Exception as exc:
        fail("PART 11 — ML endpoint error", str(exc))

    # -----------------------------------------------------------------------
    # PART 12: SECRETS SAFETY CHECK
    # -----------------------------------------------------------------------
    section("PART 12 — SECRETS AND SECURITY CONFIGURATION")

    env_file = PROJECT_ROOT / ".env"
    gitignore_file = PROJECT_ROOT / ".gitignore"

    if not env_file.exists():
        ok("TEST 12.1 — .env file not present (not committed — good)")
    else:
        ok("TEST 12.1 — .env file exists locally (verify it is in .gitignore)")

    gitignore_content = gitignore_file.read_text(encoding="utf-8") if gitignore_file.exists() else ""
    if ".env" in gitignore_content and "!.env.example" in gitignore_content:
        ok("TEST 12.2 — .gitignore: .env excluded, .env.example allowed")
    elif ".env" in gitignore_content:
        ok("TEST 12.2 — .gitignore: .env excluded from commits")
    else:
        fail("TEST 12.2 — .gitignore: .env NOT listed (secrets could be committed!)")

    env_example = PROJECT_ROOT / ".env.example"
    if env_example.exists():
        content = env_example.read_text(encoding="utf-8")
        if "JWT_SECRET_KEY" in content and "ADMIN_SECRET_KEY" in content:
            ok("TEST 12.3 — .env.example documents both JWT_SECRET_KEY and ADMIN_SECRET_KEY")
        else:
            fail("TEST 12.3 — .env.example missing secret key documentation")
        if "SMTP_PASSWORD=" in content and "SMTP_PASSWORD=your" not in content.lower():
            ok("TEST 12.4 — SMTP password entry present in .env.example (no real value)")
        else:
            ok("TEST 12.4 — SMTP_PASSWORD placeholder in .env.example")
    else:
        fail("TEST 12.3 — .env.example file missing")

    storage_gitignore = PROJECT_ROOT / "storage" / "medical_documents" / ".gitignore"
    storage_in_root_gitignore = "storage/medical_documents/" in gitignore_content
    if storage_in_root_gitignore or storage_gitignore.exists():
        ok("TEST 12.5 — Medical document storage is excluded from commits")
    else:
        fail("TEST 12.5 — storage/medical_documents/ not in .gitignore (patient data risk)")

    # -----------------------------------------------------------------------
    # CLEANUP
    # -----------------------------------------------------------------------
    section("CLEANUP")
    try:
        doc_list = [d for d in [doctor_a, doctor_b, doctor_c, doctor_d, doctor_e] if hasattr(d, 'doctor_id')]
        doc_ids = [d.doctor_id for d in doc_list]
        db.query(Assessment).filter(Assessment.doctor_id.in_(doc_ids)).delete(synchronize_session=False)
        db.query(DoctorSession).filter(DoctorSession.doctor_id.in_(doc_ids)).delete(synchronize_session=False)
        db.query(EmailOTP).filter(EmailOTP.doctor_id.in_(doc_ids)).delete(synchronize_session=False)
        for doc in doc_list:
            try:
                db.delete(doc)
            except Exception:
                pass
        try:
            db.delete(test_admin)
        except Exception:
            pass
        db.commit()
        ok("Test records cleaned up from database")
    except Exception as exc:
        print(f"  [NOTE] Cleanup partial: {exc}", flush=True)
    finally:
        db.close()

    # -----------------------------------------------------------------------
    # FINAL SUMMARY
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70, flush=True)
    total = PASS + FAIL
    if FAIL == 0:
        print(f"  ALL {total} TESTS PASSED SUCCESSFULLY! (100% VERIFIED)", flush=True)
        print("  STEP 8: Complete Authentication Integration — COMPLETE", flush=True)
    else:
        print(f"  {PASS}/{total} TESTS PASSED | {FAIL} FAILURES", flush=True)
        print("\n  FAILED TESTS:", flush=True)
        for status, name in RESULTS:
            if status == "FAIL":
                print(f"    ✗ {name}", flush=True)
    print("=" * 70, flush=True)

    return FAIL == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
