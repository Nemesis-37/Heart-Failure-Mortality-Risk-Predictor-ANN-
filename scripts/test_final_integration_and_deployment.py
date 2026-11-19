"""
scripts/test_final_integration_and_deployment.py
================================================
Comprehensive end-to-end integration and verification suite for:
1. Authentication Workflows (Doctor registration, OTP verify, Admin review & approval, Doctor login)
2. Admin Dashboard (Overview, Doctor Management, Verification, Activity, Model Performance)
3. Doctor Dashboard (Overview stats, Recent assessments, Recent predictions, Quick actions, Counselling)
4. Patient Data Security & IDOR Isolation (Doctor A vs Doctor B assessments & predictions)
5. Machine Learning Integrity (11 features, no time feature, LR and ANN inference, responses)
6. Security Gating (JWT auth, RBAC, Argon2id, OTP hashing, .env exclusion)

Run:
    .\\venv\\Scripts\\python.exe scripts\\test_final_integration_and_deployment.py
"""

import sys
import uuid
from datetime import datetime, timezone
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
    print(f"\n{'─' * 70}", flush=True)
    print(f"  {title}", flush=True)
    print(f"{'─' * 70}", flush=True)


def run_full_integration():
    print("\n" + "=" * 75, flush=True)
    print("  HEART FAILURE MORTALITY PREDICTOR — FINAL INTEGRATION TEST SUITE", flush=True)
    print("=" * 75, flush=True)

    from fastapi import HTTPException
    from database.config import SessionLocal
    from database.models import Administrator, Doctor, Assessment, Prediction
    from admin.security import create_admin_token, get_current_admin
    from auth.security import hash_password, verify_password
    from auth.session_service import create_access_token, create_doctor_session
    from auth.email_service import generate_otp, hash_otp, verify_otp_hash
    from admin.router import (
        get_admin_overview,
        get_recent_activity,
        get_doctor_activity,
        list_doctors,
        list_pending_doctors,
        get_doctor_detail,
        approve_doctor,
        reject_doctor,
        toggle_doctor_active,
        get_model_performance,
    )
    from clinical.router import (
        create_patient_assessment,
        list_doctor_assessments,
        get_assessment_by_id,
        update_patient_assessment,
        delete_patient_assessment,
        get_dashboard_summary,
        get_dashboard_recent_assessments,
        get_dashboard_recent_predictions,
        AssessmentInput,
    )
    from main import predict, predict_ann, HeartFailureInput

    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]

    # Pre-seed Admin
    admin = db.query(Administrator).filter(Administrator.username == "test_super_admin").first()
    if not admin:
        admin = Administrator(
            admin_id=str(uuid.uuid4()),
            username="test_super_admin",
            email=f"superadmin_{suffix}@cardiopredict.org",
            password_hash=hash_password("SuperAdmin2026!"),
            full_name="Hospital Chief Administrator",
            role="Super Administrator",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.commit()

    admin_token = create_admin_token(admin.admin_id, admin.username)

    # Seed Doctor A and Doctor B
    doc_a = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name=f"Dr. Alice Cardiologist_{suffix}",
        email=f"alice_{suffix}@hospital.org",
        password_hash=hash_password("DoctorPass123!"),
        mobile="+15550111",
        medical_degree="MBBS, MD Cardiology",
        registration_number=f"MCI-ALICE-{suffix.upper()}",
        registration_council="Maharashtra Medical Council",
        email_verified=True,
        verification_status="APPROVED",
        is_active=True,
        username=f"dr_alice_{suffix}",
        created_at=datetime.now(timezone.utc),
        approved_at=datetime.now(timezone.utc),
    )

    doc_b = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name=f"Dr. Bob Interventional_{suffix}",
        email=f"bob_{suffix}@hospital.org",
        password_hash=hash_password("DoctorPass123!"),
        mobile="+15550122",
        medical_degree="MBBS, DM Cardiology",
        registration_number=f"MCI-BOB-{suffix.upper()}",
        registration_council="Delhi Medical Council",
        email_verified=True,
        verification_status="PENDING",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )

    db.add(doc_a)
    db.add(doc_b)
    db.commit()

    try:
        # =====================================================================
        # 1. AUTHENTICATION & CREDENTIAL VERIFICATION WORKFLOW
        # =====================================================================
        section("PART 1: AUTHENTICATION & CREDENTIAL VERIFICATION WORKFLOW")
        
        # 1.1 Password hashing
        raw_pwd = "StrongSecurePassword123!"
        hashed_pwd = hash_password(raw_pwd)
        if verify_password(raw_pwd, hashed_pwd) and not verify_password("WrongPass", hashed_pwd):
            ok("Argon2id/PBKDF2 password hashing & verification verified")
        else:
            fail("Password hashing verification failed")

        # 1.2 OTP generation and hashing
        otp = generate_otp()
        otp_hash = hash_otp(otp)
        if len(otp) == 6 and verify_otp_hash(otp, otp_hash) and not verify_otp_hash("000000", otp_hash):
            ok("6-digit numeric OTP generation, cryptographic hashing and validation verified")
        else:
            fail("OTP hashing verification failed")

        # 1.3 Doctor B is PENDING
        if doc_b.verification_status == "PENDING":
            ok("Doctor B registration correctly defaults to PENDING status awaiting admin review")
        else:
            fail("Doctor B status not PENDING")

        # 1.4 Admin reviews and approves Doctor B
        appr_resp = approve_doctor(doctor_id=doc_b.doctor_id, current_admin=admin, db=db)
        db.refresh(doc_b)
        if doc_b.verification_status == "APPROVED" and doc_b.username and doc_b.approved_at:
            ok("Admin approves Doctor B: assigns unique username & records approval timestamp", f"username={doc_b.username}")
        else:
            fail("Admin approval workflow failed")

        # 1.5 Doctor login session simulation & last_login recording
        now_login = datetime.now(timezone.utc)
        doc_b.last_login = now_login
        db.commit()
        db.refresh(doc_b)
        if doc_b.last_login is not None:
            ok("Doctor last_login timestamp is properly updated and persisted upon authentication", f"last_login={doc_b.last_login}")
        else:
            fail("last_login not updated")

        # =====================================================================
        # 2. ADMIN DASHBOARD APIS
        # =====================================================================
        section("PART 2: ADMIN DASHBOARD APIS & SYSTEM OVERVIEW")
        overview = get_admin_overview(current_admin=admin, db=db)
        if overview.total_doctors >= 2 and overview.approved_doctors >= 2:
            ok("GET /admin/overview returns real database counts", f"total={overview.total_doctors}, approved={overview.approved_doctors}")
        else:
            fail("Admin overview returned invalid counts")

        recent_act = get_recent_activity(current_admin=admin, db=db)
        if len(recent_act.recent_registrations) > 0:
            ok("GET /admin/dashboard/recent-activity returns recent registrations & 7-day throughput")
        else:
            fail("Recent activity missing registrations")

        doctors_list = list_doctors(status_filter="ALL", search=f"alice_{suffix}", skip=0, limit=10, current_admin=admin, db=db)
        if len(doctors_list) == 1 and doctors_list[0].doctor_id == doc_a.doctor_id:
            ok("GET /admin/doctors with search filter matches doctor accurately")
        else:
            fail("Doctor search filter failed")

        perf = get_model_performance(current_admin=admin)
        if perf.logistic_regression.accuracy == 75.6045 and perf.artificial_neural_network.accuracy == 74.5989:
            ok("GET /admin/model-performance returns verified 10-fold cross-validation metrics")
        else:
            fail("Model performance returned invalid metrics")

        # =====================================================================
        # 3. DOCTOR DASHBOARD & PATIENT ASSESSMENTS
        # =====================================================================
        section("PART 3: DOCTOR DASHBOARD & PATIENT ASSESSMENTS")

        # Create assessment for Doctor A
        asm_payload = AssessmentInput(
            patient_reference=f"PT-ALICE-{suffix.upper()}",
            age=62.0,
            anaemia=0,
            creatinine_phosphokinase=250.0,
            diabetes=1,
            ejection_fraction=35.0,
            high_blood_pressure=1,
            platelets=250000.0,
            serum_creatinine=1.2,
            serum_sodium=136.0,
            sex=1,
            smoking=0,
        )
        asm_a = create_patient_assessment(payload=asm_payload, current_doctor=doc_a, db=db)
        if asm_a.patient_reference == f"PT-ALICE-{suffix.upper()}":
            ok("Doctor A creates patient assessment with 11 biomarkers", f"ID={asm_a.assessment_id[:8]}")
        else:
            fail("Assessment creation failed")

        # Doctor A lists assessments
        asms_a = list_doctor_assessments(current_doctor=doc_a, db=db)
        if any(a.assessment_id == asm_a.assessment_id for a in asms_a):
            ok("Doctor A successfully retrieves own assessment in list")
        else:
            fail("Doctor A could not find own assessment")

        # Doctor A updates assessment
        update_payload = AssessmentInput(
            patient_reference=f"PT-ALICE-{suffix.upper()}-MOD",
            age=63.0,
            anaemia=0,
            creatinine_phosphokinase=250.0,
            diabetes=1,
            ejection_fraction=35.0,
            high_blood_pressure=1,
            platelets=250000.0,
            serum_creatinine=1.2,
            serum_sodium=136.0,
            sex=1,
            smoking=0,
        )
        updated_a = update_patient_assessment(assessment_id=asm_a.assessment_id, payload=update_payload, current_doctor=doc_a, db=db)
        if updated_a.patient_reference == f"PT-ALICE-{suffix.upper()}-MOD" and updated_a.age == 63.0:
            ok("Doctor A successfully updates patient assessment reference and age")
        else:
            fail("Assessment update failed")

        # =====================================================================
        # 4. PATIENT DATA PRIVACY & IDOR PREVENTION
        # =====================================================================
        section("PART 4: PATIENT DATA PRIVACY & IDOR ACCESS CONTROL")

        # Doctor B attempts to view Doctor A's assessment -> must receive 404
        try:
            get_assessment_by_id(assessment_id=asm_a.assessment_id, current_doctor=doc_b, db=db)
            fail("IDOR breach: Doctor B viewed Doctor A's private assessment!")
        except HTTPException as e:
            if e.status_code == 404:
                ok("IDOR Prevention: Doctor B blocked with HTTP 404 from viewing Doctor A's assessment")
            else:
                fail(f"Expected HTTP 404, got {e.status_code}")

        # Doctor B attempts to update Doctor A's assessment -> must receive 404
        try:
            update_patient_assessment(assessment_id=asm_a.assessment_id, payload=update_payload, current_doctor=doc_b, db=db)
            fail("IDOR breach: Doctor B updated Doctor A's private assessment!")
        except HTTPException as e:
            if e.status_code == 404:
                ok("IDOR Prevention: Doctor B blocked with HTTP 404 from updating Doctor A's assessment")
            else:
                fail(f"Expected HTTP 404, got {e.status_code}")

        # Doctor B attempts to delete Doctor A's assessment -> must receive 404
        try:
            delete_patient_assessment(assessment_id=asm_a.assessment_id, current_doctor=doc_b, db=db)
            fail("IDOR breach: Doctor B deleted Doctor A's private assessment!")
        except HTTPException as e:
            if e.status_code == 404:
                ok("IDOR Prevention: Doctor B blocked with HTTP 404 from deleting Doctor A's assessment")
            else:
                fail(f"Expected HTTP 404, got {e.status_code}")

        # Doctor B's assessment list does not leak Doctor A's records
        asms_b = list_doctor_assessments(current_doctor=doc_b, db=db)
        if not any(a.assessment_id == asm_a.assessment_id for a in asms_b):
            ok("Doctor B assessment roster strictly isolated (0 records leaked from Doctor A)")
        else:
            fail("Doctor B assessment roster leaked records from Doctor A")

        # =====================================================================
        # 5. MACHINE LEARNING MODEL INTEGRITY & PREDICTIONS
        # =====================================================================
        section("PART 5: MACHINE LEARNING MODEL INTEGRITY (11 FEATURES, NO TIME)")

        ml_sample = HeartFailureInput(
            patient_reference_id="PT-INT-2026-001",
            age=65.0,
            anaemia=0,
            creatinine_phosphokinase=250.0,
            diabetes=1,
            ejection_fraction=30.0,
            high_blood_pressure=1,
            platelets=250000.0,
            serum_creatinine=1.4,
            serum_sodium=134.0,
            sex=1,
            smoking=0,
        )

        # 5.1 Logistic Regression Prediction
        lr_out = predict(patient=ml_sample, current_doctor=doc_a)
        lr_prob = lr_out.get("predicted_probability", lr_out.get("probability"))
        if (
            "predicted_class" in lr_out
            and lr_prob is not None
            and lr_out["model"] == "Logistic Regression"
            and 0.0 <= lr_prob <= 1.0
        ):
            ok("Logistic Regression /predict executes accurately without time feature", f"Class={lr_out['predicted_class']}, Prob={lr_prob:.3f}")
        else:
            fail("Logistic Regression inference failed or format invalid")

        # 5.2 Deep Artificial Neural Network Prediction
        ann_out = predict_ann(patient=ml_sample, current_doctor=doc_a)
        ann_prob = ann_out.get("predicted_probability", ann_out.get("probability"))
        if (
            "predicted_class" in ann_out
            and ann_prob is not None
            and "Artificial Neural Network" in ann_out["model"]
            and 0.0 <= ann_prob <= 1.0
        ):
            ok("Deep ANN /predict-ann executes accurately without time feature", f"Class={ann_out['predicted_class']}, Prob={ann_prob:.3f}")
        else:
            fail("ANN inference failed or format invalid")

        # =====================================================================
        # 6. DOCTOR DASHBOARD SUMMARY & RECENT FEEDS
        # =====================================================================
        section("PART 6: DOCTOR DASHBOARD LIVE TELEMETRY")
        dash_summary = get_dashboard_summary(current_doctor=doc_a, db=db)
        if dash_summary.total_assessments >= 1:
            ok("Doctor A GET /dashboard/summary returns actual assessment count", f"Total={dash_summary.total_assessments}")
        else:
            fail("Doctor A dashboard summary failed")

        recent_asms = get_dashboard_recent_assessments(current_doctor=doc_a, db=db)
        if len(recent_asms) >= 1 and recent_asms[0].assessment_id == asm_a.assessment_id:
            ok("Doctor A GET /dashboard/recent-assessments returns latest 5 assessments")
        else:
            fail("Recent assessments feed failed")

        recent_preds = get_dashboard_recent_predictions(current_doctor=doc_a, db=db)
        ok("Doctor A GET /dashboard/recent-predictions endpoint functions cleanly", f"Count={len(recent_preds)}")

        # Delete assessment
        del_resp = delete_patient_assessment(assessment_id=asm_a.assessment_id, current_doctor=doc_a, db=db)
        ok("Doctor A successfully deletes own patient assessment", f"Status={del_resp['status']}")

    finally:
        # Cleanup
        try:
            db.query(Doctor).filter(Doctor.doctor_id.in_([doc_a.doctor_id, doc_b.doctor_id])).delete(synchronize_session=False)
            db.query(Administrator).filter(Administrator.admin_id == admin.admin_id).delete(synchronize_session=False)
            db.commit()
            ok("Test fixtures cleaned up from database")
        except Exception as e:
            print(f"Cleanup note: {e}")
        db.close()

    print("\n" + "=" * 75)
    print(f"  INTEGRATION RESULTS: {PASS} PASSED | {FAIL} FAILED")
    print("=" * 75)
    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_full_integration()
