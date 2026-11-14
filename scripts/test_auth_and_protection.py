"""
scripts/test_auth_and_protection.py
====================================
Comprehensive Test Suite for:
- STEP 6: Secure Doctor Login, Logout, Session Security, and Rate Limiting
- STEP 7: Backend Authorization, Protected Prediction & Clinical APIs, and IDOR Prevention

Direct deterministic validation of FastAPI endpoints, security dependencies,
and database models.
Can be executed directly via:
    .\\venv\\Scripts\\python.exe scripts\\test_auth_and_protection.py
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def run_tests():
    print("\n" + "=" * 70, flush=True)
    print("  STEP 6 & STEP 7 TEST SUITE: AUTHENTICATION, AUTHORIZATION & IDOR", flush=True)
    print("=" * 70, flush=True)

    try:
        from fastapi import HTTPException
        from database.config import SessionLocal, engine
        from database.models import Base, Doctor, DoctorSession, Assessment, Prediction
        from auth.security import hash_password
        from auth.schemas import DoctorLoginRequest, RefreshRequest, LogoutRequest
        from auth.router import doctor_login, refresh_session_endpoint, doctor_logout
        from auth.dependencies import get_current_doctor
        from clinical.router import (
            AssessmentInput,
            list_doctor_assessments,
            create_patient_assessment,
            get_assessment_by_id,
            update_patient_assessment,
            delete_patient_assessment,
            get_doctor_dashboard_stats,
        )
        from main import (
            PatientData,
            predict_logistic_regression,
            predict_ann,
            get_auth_doctor,
        )
    except ImportError as e:
        print(f"[ERROR] Missing required packages: {e}", flush=True)
        return False

    db = SessionLocal()

    # Ensure tables exist
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        print(f"[WARN] Base.metadata.create_all warning: {e}", flush=True)

    run_id = uuid.uuid4().hex[:6]
    password_plain = "CardioCare2026!"
    password_hash = hash_password(password_plain)

    email_doctor_a = f"dr.carter_{run_id}@hospital.org"
    email_doctor_b = f"dr.watson_{run_id}@hospital.org"
    email_unverified = f"dr.unverified_{run_id}@hospital.org"
    email_pending = f"dr.pending_{run_id}@hospital.org"
    email_rejected = f"dr.rejected_{run_id}@hospital.org"
    email_inactive = f"dr.inactive_{run_id}@hospital.org"

    doc_a = None
    doc_b = None

    try:
        print("\n[SETUP] Seeding clinical test physician accounts...", flush=True)

        doc_a = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. Julian Carter",
            email=email_doctor_a,
            password_hash=password_hash,
            mobile="9876543210",
            medical_degree="MD, FACC",
            registration_number=f"REG-A-{run_id}",
            registration_council="General Medical Council",
            email_verified=True,
            verification_status="APPROVED",
            is_active=True,
        )

        doc_b = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. John Watson",
            email=email_doctor_b,
            password_hash=password_hash,
            mobile="9876543211",
            medical_degree="MBBS, MD",
            registration_number=f"REG-B-{run_id}",
            registration_council="Medical Council of India",
            email_verified=True,
            verification_status="APPROVED",
            is_active=True,
        )

        doc_unverified = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. Sarah Unverified",
            email=email_unverified,
            password_hash=password_hash,
            mobile="9876543212",
            medical_degree="MD",
            registration_number=f"REG-U-{run_id}",
            registration_council="State Medical Council",
            email_verified=False,
            verification_status="PENDING",
            is_active=True,
        )

        doc_pending = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. Michael Pending",
            email=email_pending,
            password_hash=password_hash,
            mobile="9876543213",
            medical_degree="MD",
            registration_number=f"REG-P-{run_id}",
            registration_council="State Medical Council",
            email_verified=True,
            verification_status="PENDING",
            is_active=True,
        )

        doc_rejected = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. Robert Rejected",
            email=email_rejected,
            password_hash=password_hash,
            mobile="9876543214",
            medical_degree="MD",
            registration_number=f"REG-R-{run_id}",
            registration_council="State Medical Council",
            email_verified=True,
            verification_status="REJECTED",
            rejection_reason="Registration certificate could not be authenticated with medical council directory.",
            is_active=True,
        )

        doc_inactive = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. Inactive Suspended",
            email=email_inactive,
            password_hash=password_hash,
            mobile="9876543215",
            medical_degree="MD",
            registration_number=f"REG-I-{run_id}",
            registration_council="State Medical Council",
            email_verified=True,
            verification_status="APPROVED",
            is_active=False,
        )

        db.add_all([doc_a, doc_b, doc_unverified, doc_pending, doc_rejected, doc_inactive])
        db.commit()
        print(f"  [OK] Successfully seeded 6 test accounts for validation run {run_id}.", flush=True)

        # =====================================================================
        # STEP 6 TESTS: DOCTOR LOGIN, LOGOUT & SESSION MANAGEMENT
        # =====================================================================
        print("\n" + "-" * 60, flush=True)
        print("  STEP 6 TESTS: SECURE PHYSICIAN LOGIN & LOGOUT", flush=True)
        print("-" * 60, flush=True)

        # TEST 6.1: Successful Login of Approved Doctor
        print("\n[TEST 6.1] Valid Doctor Login (Approved & Verified)...", flush=True)
        login_payload = DoctorLoginRequest(email=email_doctor_a, password=password_plain, remember_me=False)
        token_res = doctor_login(payload=login_payload, db=db)
        assert token_res.status == "success"
        assert token_res.access_token is not None
        assert token_res.refresh_token is not None
        assert token_res.token_type == "Bearer"
        assert token_res.doctor.email == email_doctor_a
        assert token_res.doctor.verification_status == "APPROVED"
        token_a = token_res.access_token
        refresh_a = token_res.refresh_token
        print(f"  [OK] Doctor A login successful. Received JWT ({token_a[:25]}...) and refresh token.", flush=True)

        # TEST 6.2: Invalid Password Rejection
        print("\n[TEST 6.2] Incorrect Password Rejection...", flush=True)
        try:
            doctor_login(payload=DoctorLoginRequest(email=email_doctor_a, password="WrongPassword123!"), db=db)
            assert False, "Should have raised 401 Unauthorized"
        except HTTPException as exc:
            assert exc.status_code == 401
            print(f"  [OK] Invalid password correctly rejected with HTTP 401: {exc.detail}", flush=True)

        # TEST 6.3: Unverified Email Login Rejection
        print("\n[TEST 6.3] Unverified Email Account Login Rejection...", flush=True)
        try:
            doctor_login(payload=DoctorLoginRequest(email=email_unverified, password=password_plain), db=db)
            assert False, "Should have raised 403 Forbidden"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "verified" in exc.detail.lower()
            print(f"  [OK] Unverified email blocked with HTTP 403: {exc.detail}", flush=True)

        # TEST 6.4: Pending Administrative Approval Login Rejection
        print("\n[TEST 6.4] Pending Approval Account Login Rejection...", flush=True)
        try:
            doctor_login(payload=DoctorLoginRequest(email=email_pending, password=password_plain), db=db)
            assert False, "Should have raised 403 Forbidden"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "pending" in exc.detail.lower()
            print(f"  [OK] Pending account blocked with HTTP 403: {exc.detail}", flush=True)

        # TEST 6.5: Rejected Account Login Rejection
        print("\n[TEST 6.5] Rejected Account Login Rejection (with reason)...", flush=True)
        try:
            doctor_login(payload=DoctorLoginRequest(email=email_rejected, password=password_plain), db=db)
            assert False, "Should have raised 403 Forbidden"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "rejected" in exc.detail.lower()
            assert "certificate" in exc.detail.lower()
            print(f"  [OK] Rejected account blocked with HTTP 403 & explicit reason: {exc.detail}", flush=True)

        # TEST 6.6: Inactive / Suspended Account Login Rejection
        print("\n[TEST 6.6] Inactive / Suspended Account Login Rejection...", flush=True)
        try:
            doctor_login(payload=DoctorLoginRequest(email=email_inactive, password=password_plain), db=db)
            assert False, "Should have raised 403 Forbidden"
        except HTTPException as exc:
            assert exc.status_code == 403
            assert "suspended" in exc.detail.lower() or "deactivated" in exc.detail.lower()
            print(f"  [OK] Inactive account blocked with HTTP 403: {exc.detail}", flush=True)

        # TEST 6.7: Refresh Token Rotation
        print("\n[TEST 6.7] Refresh Token Rotation (/auth/refresh)...", flush=True)
        refresh_res = refresh_session_endpoint(payload=RefreshRequest(refresh_token=refresh_a), db=db)
        new_token_a = refresh_res.access_token
        new_refresh_a = refresh_res.refresh_token
        assert new_refresh_a != refresh_a, "Refresh token should have rotated!"
        print("  [OK] Token rotated successfully. New access token and refresh token issued.", flush=True)

        # Re-using the old refresh token must be rejected
        try:
            refresh_session_endpoint(payload=RefreshRequest(refresh_token=refresh_a), db=db)
            assert False, "Old revoked refresh token should have raised 401"
        except HTTPException as exc:
            assert exc.status_code == 401
            print("  [OK] Revoked/used refresh token successfully rejected with HTTP 401.", flush=True)

        # TEST 6.8: Secure Logout
        print("\n[TEST 6.8] Secure Logout & Session Revocation (/auth/logout)...", flush=True)
        logout_res = doctor_logout(payload=LogoutRequest(refresh_token=new_refresh_a), db=db)
        assert logout_res["status"] == "success"
        # Trying to refresh after logout must fail
        try:
            refresh_session_endpoint(payload=RefreshRequest(refresh_token=new_refresh_a), db=db)
            assert False, "Session after logout should be revoked (HTTP 401)"
        except HTTPException as exc:
            assert exc.status_code == 401
            print("  [OK] Logout revoked the session in database. Subsequent refresh rejected with HTTP 401.", flush=True)

        # Re-login Doctor A to obtain an active token for Step 7 tests
        login_res_a = doctor_login(
            payload=DoctorLoginRequest(email=email_doctor_a, password=password_plain),
            db=db,
        )
        active_token_a = login_res_a.access_token
        auth_header_a = f"Bearer {active_token_a}"

        # Login Doctor B to obtain Doctor B's token
        login_res_b = doctor_login(
            payload=DoctorLoginRequest(email=email_doctor_b, password=password_plain),
            db=db,
        )
        active_token_b = login_res_b.access_token
        auth_header_b = f"Bearer {active_token_b}"

        # =====================================================================
        # STEP 7 TESTS: PROTECTED APIS & IDOR SECURITY
        # =====================================================================
        print("\n" + "-" * 60, flush=True)
        print("  STEP 7 TESTS: PROTECTED DASHBOARD, APIS & IDOR ENFORCEMENT", flush=True)
        print("-" * 60, flush=True)

        # TEST 7.1: Protected Dependency Without Authorization Header
        print("\n[TEST 7.1] Accessing Protected Dependency Without Token...", flush=True)
        try:
            get_auth_doctor(authorization="")
            assert False, "Should have raised 401"
        except HTTPException as exc:
            assert exc.status_code == 401
            print(f"  [OK] Missing authorization rejected with HTTP 401: {exc.detail}", flush=True)

        # TEST 7.2: Protected Dependency With Malformed / Invalid Token
        print("\n[TEST 7.2] Accessing Protected Dependency With Invalid Token...", flush=True)
        try:
            get_current_doctor(authorization="Bearer bad.token.value", db=db)
            assert False, "Should have raised 401"
        except HTTPException as exc:
            assert exc.status_code == 401
            print("  [OK] Invalid signature token rejected with HTTP 401.", flush=True)

        # TEST 7.3: Authenticated Doctor A Creates Patient Assessment
        print("\n[TEST 7.3] Doctor A Creates Patient Assessment (/api/assessments)...", flush=True)
        patient_payload = AssessmentInput(
            patient_reference_id=f"PT-ALPHA-{run_id}",
            age=64.0,
            anaemia=1,
            creatinine_phosphokinase=320.0,
            diabetes=0,
            ejection_fraction=30.0,
            high_blood_pressure=1,
            platelets=250000.0,
            serum_creatinine=1.4,
            serum_sodium=136.0,
            sex=1,
            smoking=0,
        )
        # Verify get_current_doctor dependency resolves doctor A
        verified_doc_a = get_current_doctor(authorization=auth_header_a, db=db)
        assert verified_doc_a.doctor_id == doc_a.doctor_id

        verified_doc_b = get_current_doctor(authorization=auth_header_b, db=db)
        assert verified_doc_b.doctor_id == doc_b.doctor_id

        assessment_a = create_patient_assessment(
            payload=patient_payload,
            current_doctor=verified_doc_a,
            db=db,
        )
        assessment_a_id = str(assessment_a.id)
        assert assessment_a.doctor_id == doc_a.doctor_id
        print(f"  [OK] Assessment {assessment_a.assessment_code} created under Doctor A ({assessment_a_id}).", flush=True)

        # TEST 7.4: IDOR Protection: Doctor B Tries To Read Doctor A's Assessment
        print("\n[TEST 7.4] IDOR Test: Doctor B Attempts to Read Doctor A's Assessment...", flush=True)
        try:
            get_assessment_by_id(
                assessment_id=assessment_a_id,
                current_doctor=verified_doc_b,
                db=db,
            )
            assert False, "IDOR check failed! Doctor B was able to read Doctor A's assessment."
        except HTTPException as exc:
            assert exc.status_code == 403
            print(f"  [OK] IDOR prevented! Doctor B blocked with HTTP 403: {exc.detail}", flush=True)

        # TEST 7.5: IDOR Protection: Doctor B Tries To Modify Doctor A's Assessment
        print("\n[TEST 7.5] IDOR Test: Doctor B Attempts to Modify Doctor A's Assessment...", flush=True)
        try:
            update_patient_assessment(
                assessment_id=assessment_a_id,
                payload=patient_payload,
                current_doctor=verified_doc_b,
                db=db,
            )
            assert False, "IDOR check failed! Doctor B was able to modify Doctor A's assessment."
        except HTTPException as exc:
            assert exc.status_code == 403
            print(f"  [OK] IDOR prevented! Doctor B cannot update Doctor A's record (HTTP 403): {exc.detail}", flush=True)

        # TEST 7.6: IDOR Protection: Doctor B Tries To Delete Doctor A's Assessment
        print("\n[TEST 7.6] IDOR Test: Doctor B Attempts to Delete Doctor A's Assessment...", flush=True)
        try:
            delete_patient_assessment(
                assessment_id=assessment_a_id,
                current_doctor=verified_doc_b,
                db=db,
            )
            assert False, "IDOR check failed! Doctor B was able to delete Doctor A's assessment."
        except HTTPException as exc:
            assert exc.status_code == 403
            print(f"  [OK] IDOR prevented! Doctor B cannot delete Doctor A's record (HTTP 403): {exc.detail}", flush=True)

        # TEST 7.7: Listing Scoped Strictly To Calling Doctor
        print("\n[TEST 7.7] Assessment List Isolation (Doctor B cannot see Doctor A's records)...", flush=True)
        list_a = list_doctor_assessments(current_doctor=verified_doc_a, db=db)
        list_b = list_doctor_assessments(current_doctor=verified_doc_b, db=db)
        assert any(item.id == assessment_a_id for item in list_a), "Doctor A should see their own assessment."
        assert not any(item.id == assessment_a_id for item in list_b), "Doctor B must NOT see Doctor A's assessment."
        print(f"  [OK] Complete data isolation: Doctor A sees {len(list_a)} record(s); Doctor B sees {len(list_b)} record(s).", flush=True)

        # TEST 7.8: Protected Prediction Endpoints
        print("\n[TEST 7.8] Protected Model Prediction Endpoints (/predict & /predict-ann)...", flush=True)
        predict_input = PatientData(
            age=60.0,
            anaemia=0,
            creatinine_phosphokinase=250.0,
            diabetes=0,
            ejection_fraction=38.0,
            high_blood_pressure=0,
            platelets=260000.0,
            serum_creatinine=1.1,
            serum_sodium=137.0,
            sex=1,
            smoking=0,
        )
        # Logistic Regression with verified physician
        lr_out = predict_logistic_regression(patient=predict_input, current_doctor=verified_doc_a)
        assert "predicted_class" in lr_out and "predicted_probability" in lr_out
        assert lr_out["model"] == "Logistic Regression"
        print(f"  [OK] Protected Logistic Regression executed: Class {lr_out['predicted_class']} ({lr_out['predicted_probability']:.1%}).", flush=True)

        # ANN with verified physician
        ann_out = predict_ann(patient=predict_input, current_doctor=verified_doc_a)
        assert "predicted_class" in ann_out and "predicted_probability" in ann_out
        assert ann_out["model"] == "Artificial Neural Network"
        print(f"  [OK] Protected ANN executed: Class {ann_out['predicted_class']} ({ann_out['predicted_probability']:.1%}).", flush=True)

        # TEST 7.9: Protected Dashboard Statistics
        print("\n[TEST 7.9] Protected Clinical Dashboard Stats (/api/dashboard/stats)...", flush=True)
        stats_out = get_doctor_dashboard_stats(current_doctor=verified_doc_a, db=db)
        assert stats_out.total_assessments >= 1
        print(f"  [OK] Dashboard stats retrieved for Doctor A: Total assessments = {stats_out.total_assessments}.", flush=True)

        print("\n" + "=" * 70, flush=True)
        print("  ALL STEP 6 & STEP 7 TESTS PASSED SUCCESSFULLY! (100% VERIFIED)", flush=True)
        print("=" * 70, flush=True)
        return True

    finally:
        try:
            if doc_a:
                db.query(Assessment).filter(Assessment.doctor_id == doc_a.doctor_id).delete()
                db.query(DoctorSession).filter(DoctorSession.doctor_id == doc_a.doctor_id).delete()
            if doc_b:
                db.query(Assessment).filter(Assessment.doctor_id == doc_b.doctor_id).delete()
                db.query(DoctorSession).filter(DoctorSession.doctor_id == doc_b.doctor_id).delete()
            db.query(Doctor).filter(Doctor.email.in_([
                email_doctor_a, email_doctor_b, email_unverified,
                email_pending, email_rejected, email_inactive
            ])).delete(synchronize_session=False)
            db.commit()
            print("  [CLEANUP] Test physician accounts and test assessments removed cleanly.", flush=True)
        except Exception as e:
            print(f"  [CLEANUP NOTE] {e}", flush=True)
        finally:
            db.close()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
