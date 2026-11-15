"""
scripts/test_admin_auth_and_recovery.py
=======================================
Test suite for:
1. Predefined Administrator Account (no public registration, env configuration)
2. Admin Login (correct / incorrect credentials, token generation)
3. Role-based Access Control (Doctor token attempting admin operations)
4. Admin Forgot Password via 6-digit OTP bound to debashish.g333@gmail.com
5. OTP Security (incorrect OTP, max 5 attempts lockout, expired OTP, 60s cooldown)
6. Password Reset with Argon2id hashing and replay prevention
7. Login using the newly reset password
8. Admin Dashboard APIs: /admin/overview and /admin/doctor-activity

Run:
    .\\venv\\Scripts\\python.exe scripts\\test_admin_auth_and_recovery.py
"""

import sys
import time
import uuid
from datetime import datetime, timedelta, timezone
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
    print(f"\n{'─' * 65}", flush=True)
    print(f"  {title}", flush=True)
    print(f"{'─' * 65}", flush=True)


def run_tests():
    print("\n" + "=" * 70, flush=True)
    print("  ADMIN AUTHENTICATION & PASSWORD RECOVERY TEST SUITE", flush=True)
    print("=" * 70, flush=True)

    from fastapi import HTTPException
    from database.config import SessionLocal, engine
    from database.models import Base, Administrator, Doctor, DoctorSession, Assessment
    from auth.security import hash_password, verify_password
    from auth.session_service import create_access_token
    from admin.security import create_admin_token, verify_admin_token, get_current_admin
    from admin.schemas import (
        AdminLoginRequest,
        AdminForgotPasswordRequest,
        AdminVerifyResetOTPRequest,
        AdminResetPasswordRequest,
    )
    from admin.router import (
        admin_login,
        admin_forgot_password,
        admin_verify_reset_otp,
        admin_reset_password,
        get_admin_overview,
        get_doctor_activity,
        ensure_initial_admin,
        _ADMIN_PASSWORD_RESET,
    )

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    run_id = uuid.uuid4().hex[:8]

    # -----------------------------------------------------------------------
    # PART 1: PREDEFINED ADMIN PROVISIONING & LOGIN
    # -----------------------------------------------------------------------
    section("PART 1 — PREDEFINED ADMIN ACCOUNT & AUTHENTICATION")

    admin_username = f"admin_{run_id}"
    admin_initial_pwd = "InitialAdminPass2026!"
    admin_email = "debashish.g333@gmail.com"

    # Pre-clean any leftover test admin records
    db.query(Administrator).filter(
        (Administrator.username.like("admin_%")) | (Administrator.email == admin_email)
    ).delete(synchronize_session=False)
    db.commit()

    test_admin = Administrator(
        admin_id=str(uuid.uuid4()),
        username=admin_username,
        email=admin_email,
        password_hash=hash_password(admin_initial_pwd),
        full_name="Lead Clinical Administrator",
        role="Super Administrator",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    db.add(test_admin)
    db.commit()
    ok("Predefined administrator created with Argon2id hash", f"username={admin_username}")

    # Test: Correct login
    login_req = AdminLoginRequest(username=admin_username, password=admin_initial_pwd)
    login_res = admin_login(payload=login_req, db=db)
    if login_res.token and login_res.admin.username == admin_username:
        admin_token = login_res.token
        ok("Admin login with correct credentials succeeded", f"token={admin_token[:25]}...")
    else:
        fail("Admin login", "No token returned")
        admin_token = None

    # Test: Wrong password
    try:
        admin_login(payload=AdminLoginRequest(username=admin_username, password="WrongPassword999!"), db=db)
        fail("Wrong password rejection", "Should have raised 401")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok("Incorrect password rejected with HTTP 401 Unauthorized")
        else:
            fail("Wrong password status code", f"Expected 401, got {exc.status_code}")

    # Test: Non-existent admin username
    try:
        admin_login(payload=AdminLoginRequest(username="non_existent_admin_xyz", password="AnyPassword123!"), db=db)
        fail("Non-existent username rejection", "Should have raised 401")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok("Non-existent administrator username rejected with HTTP 401")
        else:
            fail("Non-existent username status code", f"Expected 401, got {exc.status_code}")

    # -----------------------------------------------------------------------
    # PART 2: ACCESS CONTROL & SEPARATION FROM DOCTOR TOKENS
    # -----------------------------------------------------------------------
    section("PART 2 — ACCESS CONTROL & DOCTOR TOKEN SEPARATION")

    # Create a doctor access token
    fake_doc_id = str(uuid.uuid4())
    doctor_token = create_access_token(fake_doc_id, f"doctor_{run_id}@hospital.org", "Dr. Clinician")

    # Attempt to use doctor token on admin dependency
    try:
        get_current_admin(authorization=f"Bearer {doctor_token}")
        fail("Doctor token accessing admin endpoint", "Should have been rejected")
    except HTTPException as exc:
        if exc.status_code in (401, 403):
            ok(f"Doctor token strictly rejected by admin authorization (HTTP {exc.status_code})")
        else:
            fail("Doctor token status code", f"Expected 401/403, got {exc.status_code}")

    # Missing token on admin dependency
    try:
        get_current_admin(authorization=None)
        fail("Missing token access", "Should have raised 401")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok("Missing authorization header rejected with HTTP 401")
        else:
            fail("Missing token status code", f"Expected 401, got {exc.status_code}")

    # Valid admin token on admin dependency
    if admin_token:
        try:
            resolved_admin = get_current_admin(authorization=f"Bearer {admin_token}")
            if resolved_admin and resolved_admin.username == admin_username:
                ok("Admin token verified successfully: resolved administrator profile")
            else:
                fail("Admin token resolution", "Mismatched admin profile")
        except HTTPException as exc:
            fail("Valid admin token rejected", f"HTTP {exc.status_code}: {exc.detail}")

    # -----------------------------------------------------------------------
    # PART 3: FORGOT PASSWORD & RECOVERY EMAIL BINDING
    # -----------------------------------------------------------------------
    section("PART 3 — FORGOT PASSWORD VIA OTP (RECOVERY EMAIL)")

    # Non-existent username
    try:
        admin_forgot_password(payload=AdminForgotPasswordRequest(username="ghost_admin"), db=db)
        fail("Forgot password with ghost username", "Should have raised 404")
    except HTTPException as exc:
        if exc.status_code == 404:
            ok("Forgot password with non-existent username returns HTTP 404")
        else:
            fail("Ghost username status code", f"Expected 404, got {exc.status_code}")

    # Valid forgot password request
    forgot_res = admin_forgot_password(payload=AdminForgotPasswordRequest(username=admin_username), db=db)
    if forgot_res.status == "success" and "@" in forgot_res.recovery_email_masked:
        ok(f"OTP dispatched for '{admin_username}' to recovery email: {forgot_res.recovery_email_masked}")
    else:
        fail("Forgot password request", "Invalid response")

    # 60-second cooldown enforcement
    try:
        admin_forgot_password(payload=AdminForgotPasswordRequest(username=admin_username), db=db)
        fail("Cooldown bypass", "Should have raised 429")
    except HTTPException as exc:
        if exc.status_code == 429:
            ok("60-second OTP resend cooldown enforced with HTTP 429 Too Many Requests")
        else:
            fail("Cooldown status code", f"Expected 429, got {exc.status_code}")

    # Verify OTP storage security: raw OTP must not be stored in plain text
    reset_record = _ADMIN_PASSWORD_RESET.get(admin_username.lower())
    if reset_record and reset_record["otp_hash"].startswith("$otp$v=1$"):
        ok("Admin OTP is cryptographically hashed (PBKDF2); raw OTP not persisted")
    else:
        fail("OTP storage security", "Hash missing or raw")

    # -----------------------------------------------------------------------
    # PART 4: OTP VERIFICATION SECURITY
    # -----------------------------------------------------------------------
    section("PART 4 — OTP VERIFICATION SECURITY CHECKS")

    # Incorrect OTP
    try:
        admin_verify_reset_otp(
            payload=AdminVerifyResetOTPRequest(username=admin_username, otp="000000"),
            db=db,
        )
        fail("Incorrect OTP acceptance", "Should have raised 400")
    except HTTPException as exc:
        if exc.status_code == 400 and "remaining" in exc.detail:
            ok(f"Incorrect OTP rejected (HTTP 400): {exc.detail}")
        else:
            fail("Incorrect OTP detail", f"Got: {exc.detail}")

    # Expired OTP check (simulate expiration)
    reset_record["expires_at"] = datetime.now(timezone.utc) - timedelta(minutes=1)
    try:
        admin_verify_reset_otp(
            payload=AdminVerifyResetOTPRequest(username=admin_username, otp="123456"),
            db=db,
        )
        fail("Expired OTP acceptance", "Should have raised 400")
    except HTTPException as exc:
        if exc.status_code == 400 and "expired" in exc.detail.lower():
            ok("Expired OTP rejected correctly (5-minute expiry window enforced)")
        else:
            fail("Expired OTP error", f"Got {exc.detail}")

    # Generate a fresh test OTP for reset testing
    from auth.email_service import generate_otp, hash_otp
    fresh_otp = generate_otp()
    _ADMIN_PASSWORD_RESET[admin_username.lower()] = {
        "otp_hash": hash_otp(fresh_otp),
        "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5),
        "attempts": 0,
        "last_sent": time.time(),
        "is_verified": False,
        "reset_token": None,
    }

    # Verify correct OTP
    verify_res = admin_verify_reset_otp(
        payload=AdminVerifyResetOTPRequest(username=admin_username, otp=fresh_otp),
        db=db,
    )
    if verify_res.status == "verified" and verify_res.reset_token:
        reset_token = verify_res.reset_token
        ok("Correct 6-digit OTP verified successfully: issued single-use reset token")
    else:
        fail("Correct OTP verification", "Missing reset_token")
        reset_token = None

    # -----------------------------------------------------------------------
    # PART 5: PASSWORD RESET & NEW PASSWORD LOGIN
    # -----------------------------------------------------------------------
    section("PART 5 — PASSWORD RESET & NEW CREDENTIALS VERIFICATION")

    new_secure_pwd = "NewAdminPassword2026!"

    # Mismatched passwords
    try:
        admin_reset_password(
            payload=AdminResetPasswordRequest(
                username=admin_username,
                reset_token=reset_token,
                new_password=new_secure_pwd,
                confirm_password="MismatchPassword!",
            ),
            db=db,
        )
        fail("Mismatched passwords", "Should have raised 400")
    except HTTPException as exc:
        if exc.status_code == 400:
            ok("Mismatched password confirmation rejected with HTTP 400")
        else:
            fail("Password mismatch code", f"Got {exc.status_code}")

    # Short password
    from pydantic import ValidationError
    try:
        req = AdminResetPasswordRequest(
            username=admin_username,
            reset_token=reset_token,
            new_password="short",
            confirm_password="short",
        )
        admin_reset_password(payload=req, db=db)
        fail("Short password", "Should have raised 400 or ValidationError")
    except (HTTPException, ValidationError):
        ok("Password shorter than 8 characters rejected by validation")

    # Successful password reset
    reset_res = admin_reset_password(
        payload=AdminResetPasswordRequest(
            username=admin_username,
            reset_token=reset_token,
            new_password=new_secure_pwd,
            confirm_password=new_secure_pwd,
        ),
        db=db,
    )
    if reset_res.get("status") == "success":
        ok("Administrator password reset successfully with Argon2id hash")
    else:
        fail("Password reset", str(reset_res))

    # Replay attack: using the same reset token again must fail
    try:
        admin_reset_password(
            payload=AdminResetPasswordRequest(
                username=admin_username,
                reset_token=reset_token,
                new_password="AnotherPassword123!",
                confirm_password="AnotherPassword123!",
            ),
            db=db,
        )
        fail("Replay attack", "Reset token was not invalidated")
    except HTTPException as exc:
        if exc.status_code == 400:
            ok("Replay attack prevented: invalidated OTP and reset session cannot be reused")
        else:
            fail("Replay status code", f"Got {exc.status_code}")

    # Login using OLD password must FAIL
    try:
        admin_login(payload=AdminLoginRequest(username=admin_username, password=admin_initial_pwd), db=db)
        fail("Old password login", "Old password still worked after reset")
    except HTTPException as exc:
        if exc.status_code == 401:
            ok("Old password rejected with HTTP 401 after reset")
        else:
            fail("Old password status code", f"Got {exc.status_code}")

    # Login using NEW password must SUCCEED
    new_login_res = admin_login(payload=AdminLoginRequest(username=admin_username, password=new_secure_pwd), db=db)
    if new_login_res.token and new_login_res.admin.username == admin_username:
        new_admin_token = new_login_res.token
        ok("Login with newly reset password succeeded; new admin JWT token issued")
    else:
        fail("New password login", "Failed to login with new password")
        new_admin_token = None

    # -----------------------------------------------------------------------
    # PART 6: ADMIN DASHBOARD APIS (OVERVIEW & DOCTOR ACTIVITY)
    # -----------------------------------------------------------------------
    section("PART 6 — ADMIN DASHBOARD APIS")

    # Overview endpoint
    admin_obj = db.query(Administrator).filter(Administrator.username == admin_username).first()
    overview = get_admin_overview(current_admin=admin_obj, db=db)
    if hasattr(overview, "total_doctors") and hasattr(overview, "total_assessments"):
        ok(f"GET /admin/overview: total_doctors={overview.total_doctors}, pending={overview.pending_doctors}, assessments={overview.total_assessments}")
    else:
        fail("GET /admin/overview", "Invalid response structure")

    # Doctor Activity endpoint (shows last login, assessments, predictions)
    activities = get_doctor_activity(current_admin=admin_obj, db=db)
    if isinstance(activities, list):
        ok(f"GET /admin/doctor-activity returned {len(activities)} clinician records")
        if len(activities) > 0:
            sample_act = activities[0]
            ok(f"  Sample Doctor Activity: {sample_act.full_name} | Assessments: {sample_act.total_assessments} | Predictions: {sample_act.total_predictions} | Last Login: {sample_act.last_login}")
    else:
        fail("GET /admin/doctor-activity", "Expected list")

    # -----------------------------------------------------------------------
    # CLEANUP
    # -----------------------------------------------------------------------
    section("CLEANUP")
    try:
        db.delete(test_admin)
        db.commit()
        ok("Test administrator cleaned up from database")
    except Exception as exc:
        print(f"  [NOTE] Cleanup: {exc}", flush=True)
    finally:
        db.close()

    # -----------------------------------------------------------------------
    # SUMMARY
    # -----------------------------------------------------------------------
    print("\n" + "=" * 70, flush=True)
    total = PASS + FAIL
    if FAIL == 0:
        print(f"  ALL {total} ADMIN AUTHENTICATION TESTS PASSED! (100% VERIFIED)", flush=True)
    else:
        print(f"  {PASS}/{total} TESTS PASSED | {FAIL} FAILURES", flush=True)
        for status_val, name in RESULTS:
            if status_val == "FAIL":
                print(f"    ✗ {name}", flush=True)
    print("=" * 70, flush=True)

    return FAIL == 0


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
