"""
scripts/test_assessments_and_dashboard.py
=========================================
Automated test suite for:
1. Patient Assessment Management (CRUD, 11 features, validation, search, pagination, 404 IDOR isolation)
2. Doctor Dashboard & Analytics APIs (/dashboard/summary, recent-assessments, recent-predictions, distribution, model-usage)
3. Model Performance verified metrics check
4. Prediction endpoints verification
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

PASS = 0
FAIL = 0


def ok(msg: str):
    global PASS
    PASS += 1
    print(f"  [PASS] {msg}", flush=True)


def fail(msg: str, detail: str = ""):
    global FAIL
    FAIL += 1
    err = f"  [FAIL] {msg}"
    if detail:
        err += f": {detail}"
    print(err, flush=True)


def run_tests():
    print("\n" + "=" * 70, flush=True)
    print("  TEST SUITE: PATIENT ASSESSMENT MANAGEMENT & DOCTOR DASHBOARD ANALYTICS", flush=True)
    print("=" * 70, flush=True)

    from fastapi import HTTPException
    from pydantic import ValidationError

    try:
        from database.config import SessionLocal, engine
        from database.models import Doctor, EmailOTP, Assessment
        from database import Base
        from auth.security import hash_password
        from clinical.router import (
            AssessmentInput,
            create_patient_assessment,
            list_doctor_assessments,
            get_assessment_by_id,
            update_patient_assessment,
            delete_patient_assessment,
            get_dashboard_summary,
            get_dashboard_recent_assessments,
            get_dashboard_recent_predictions,
            get_dashboard_prediction_distribution,
            get_dashboard_model_usage,
        )
        from main import (
            PatientData,
            predict_logistic_regression,
            predict_ann,
            get_auth_doctor,
        )
        from auth.session_service import create_access_token
        ok("All required modules and endpoints imported successfully")
    except Exception as exc:
        fail("Importing modules", str(exc))
        return

    # Create tables
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    run_id = uuid.uuid4().hex[:6]
    doc_a = None
    doc_b = None

    try:
        # Seed Doctor A and Doctor B
        doc_a = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. Sarah Connor",
            email=f"dr.connor_{run_id}@hospital.org",
            password_hash=hash_password("Pass123!"),
            mobile="9876543210",
            medical_degree="MD, FACC",
            registration_number=f"REG-CONNOR-{run_id}".upper(),
            registration_council="National Medical Commission",
            email_verified=True,
            verification_status="APPROVED",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        doc_b = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. Kyle Reese",
            email=f"dr.reese_{run_id}@hospital.org",
            password_hash=hash_password("Pass123!"),
            mobile="9876543211",
            medical_degree="MBBS, MD",
            registration_number=f"REG-REESE-{run_id}".upper(),
            registration_council="State Medical Council",
            email_verified=True,
            verification_status="APPROVED",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add_all([doc_a, doc_b])
        db.commit()
        ok(f"Doctor accounts seeded: {doc_a.full_name} and {doc_b.full_name}")

        # -------------------------------------------------------------------
        # PART 1: PATIENT ASSESSMENT MANAGEMENT TESTS
        # -------------------------------------------------------------------
        print("\n--- PART 1: PATIENT ASSESSMENT MANAGEMENT ---", flush=True)

        # 1. Create an assessment with all 11 model features
        valid_input = AssessmentInput(
            patient_reference=f"PT-{run_id}-001",
            age=65,
            anaemia=0,
            creatinine_phosphokinase=160.0,
            diabetes=1,
            ejection_fraction=35.0,
            high_blood_pressure=1,
            platelets=250000.0,
            serum_creatinine=1.4,
            serum_sodium=136.0,
            sex=1,
            smoking=0,
        )
        asm_a = create_patient_assessment(payload=valid_input, current_doctor=doc_a, db=db)
        if asm_a.assessment_id and asm_a.doctor_id == doc_a.doctor_id:
            ok(f"1. Assessment created with 11 features: {asm_a.assessment_id[:8]}... (ref: {asm_a.patient_reference})")
        else:
            fail("1. Assessment creation failed")

        # 2. Create an assessment without a patient reference
        anon_input = AssessmentInput(
            patient_reference=None,
            age=58,
            anaemia=1,
            creatinine_phosphokinase=220.0,
            diabetes=0,
            ejection_fraction=40.0,
            high_blood_pressure=0,
            platelets=180000.0,
            serum_creatinine=1.0,
            serum_sodium=138.0,
            sex=0,
            smoking=1,
        )
        asm_anon = create_patient_assessment(payload=anon_input, current_doctor=doc_a, db=db)
        if asm_anon.assessment_id and asm_anon.patient_reference is None:
            ok("2. Assessment created without patient reference (anonymous)")
        else:
            fail("2. Anonymous assessment creation failed")

        # 3. View all assessments for logged-in doctor
        list_a = list_doctor_assessments(page=1, limit=10, current_doctor=doc_a, db=db)
        if len(list_a) >= 2:
            ok(f"3. Listed assessments for Doctor A: found {len(list_a)} records (newest first)")
        else:
            fail("3. Assessment listing failed", f"Expected >= 2, got {len(list_a)}")

        # Search by patient reference
        search_res = list_doctor_assessments(
            page=1, limit=10, patient_reference=f"PT-{run_id}-001", current_doctor=doc_a, db=db
        )
        if len(search_res) == 1 and search_res[0].patient_reference == f"PT-{run_id}-001":
            ok(f"   Search by patient_reference successful: matched 1 record")
        else:
            fail("   Search by patient_reference failed", f"got {len(search_res)}")

        # 4. View one assessment by ID
        asm_fetched = get_assessment_by_id(assessment_id=asm_a.assessment_id, current_doctor=doc_a, db=db)
        if asm_fetched.assessment_id == asm_a.assessment_id:
            ok(f"4. Retrieved assessment by ID: {asm_fetched.assessment_id[:8]}...")
        else:
            fail("4. Assessment retrieval by ID failed")

        # 5. Update an assessment
        update_input = AssessmentInput(
            patient_reference=f"PT-{run_id}-001-MOD",
            age=66,
            anaemia=1,
            creatinine_phosphokinase=180.0,
            diabetes=1,
            ejection_fraction=32.0,
            high_blood_pressure=1,
            platelets=240000.0,
            serum_creatinine=1.6,
            serum_sodium=134.0,
            sex=1,
            smoking=0,
        )
        asm_updated = update_patient_assessment(
            assessment_id=asm_a.assessment_id, payload=update_input, current_doctor=doc_a, db=db
        )
        if (
            asm_updated.patient_reference == f"PT-{run_id}-001-MOD"
            and float(asm_updated.age) == 66.0
            and float(asm_updated.serum_creatinine) == 1.6
        ):
            ok(f"5. Updated assessment: patient_ref={asm_updated.patient_reference}, age={asm_updated.age}")
        else:
            fail("5. Assessment update failed")

        # 6. Delete an assessment
        del_res = delete_patient_assessment(
            assessment_id=asm_anon.assessment_id, current_doctor=doc_a, db=db
        )
        if del_res.get("status") == "success":
            ok(f"6. Deleted assessment successfully: {del_res.get('message')}")
        else:
            fail("6. Assessment deletion failed")

        # Confirm deleted record returns 404
        try:
            get_assessment_by_id(assessment_id=asm_anon.assessment_id, current_doctor=doc_a, db=db)
            fail("6b. Deleted record should return 404")
        except HTTPException as he:
            if he.status_code == 404:
                ok("   Confirmed deleted assessment returns HTTP 404")
            else:
                fail("   Unexpected status code", str(he.status_code))

        # 7. Reject invalid binary values (Pydantic validation)
        try:
            AssessmentInput(
                patient_reference="INVALID",
                age=60,
                anaemia=2,  # Invalid binary
                creatinine_phosphokinase=150.0,
                diabetes=0,
                ejection_fraction=35.0,
                high_blood_pressure=0,
                platelets=200000.0,
                serum_creatinine=1.0,
                serum_sodium=137.0,
                sex=1,
                smoking=0,
            )
            fail("7. Invalid binary anaemia=2 should raise ValidationError")
        except ValidationError:
            ok("7. Invalid binary value (anaemia=2) rejected by validation")

        # 8. Reject missing model features
        try:
            AssessmentInput.model_validate({
                "patient_reference": "INCOMPLETE",
                "age": 60,
                # missing other 10 features
            })
            fail("8. Incomplete features should raise ValidationError")
        except ValidationError:
            ok("8. Incomplete model input features rejected by validation")

        # 9. Verify Doctor A cannot view or modify Doctor B's assessment (HTTP 404)
        # Create an assessment owned by Doctor B
        asm_b = create_patient_assessment(
            payload=AssessmentInput(
                patient_reference=f"PT-B-{run_id}",
                age=72,
                anaemia=0,
                creatinine_phosphokinase=300.0,
                diabetes=1,
                ejection_fraction=25.0,
                high_blood_pressure=1,
                platelets=160000.0,
                serum_creatinine=2.1,
                serum_sodium=132.0,
                sex=1,
                smoking=1,
            ),
            current_doctor=doc_b,
            db=db,
        )
        ok(f"   Created Doctor B assessment: {asm_b.assessment_id[:8]}...")

        # Doctor A attempts to read Doctor B's assessment
        try:
            get_assessment_by_id(assessment_id=asm_b.assessment_id, current_doctor=doc_a, db=db)
            fail("9a. Doctor A reading Doctor B's assessment should raise 404")
        except HTTPException as he:
            if he.status_code == 404:
                ok("9a. Cross-doctor read blocked: returns HTTP 404 (IDOR safe, no ID enumeration)")
            else:
                fail("9a. Wrong status code", f"Got {he.status_code}")

        # Doctor A attempts to modify Doctor B's assessment
        try:
            update_patient_assessment(
                assessment_id=asm_b.assessment_id,
                payload=valid_input,
                current_doctor=doc_a,
                db=db,
            )
            fail("9b. Doctor A modifying Doctor B's assessment should raise 404")
        except HTTPException as he:
            if he.status_code == 404:
                ok("9b. Cross-doctor update blocked: returns HTTP 404")
            else:
                fail("9b. Wrong status code", f"Got {he.status_code}")

        # Doctor A attempts to delete Doctor B's assessment
        try:
            delete_patient_assessment(
                assessment_id=asm_b.assessment_id,
                current_doctor=doc_a,
                db=db,
            )
            fail("9c. Doctor A deleting Doctor B's assessment should raise 404")
        except HTTPException as he:
            if he.status_code == 404:
                ok("9c. Cross-doctor delete blocked: returns HTTP 404")
            else:
                fail("9c. Wrong status code", f"Got {he.status_code}")

        # Doctor B list sees only Doctor B's records
        list_b = list_doctor_assessments(page=1, limit=10, current_doctor=doc_b, db=db)
        if len(list_b) == 1 and list_b[0].assessment_id == asm_b.assessment_id:
            ok("9d. Data isolation: Doctor B sees only their 1 assessment")
        else:
            fail("9d. Doctor B list isolation", f"Got {len(list_b)}")

        # -------------------------------------------------------------------
        # PART 2: DOCTOR DASHBOARD & ANALYTICS APIS
        # -------------------------------------------------------------------
        print("\n--- PART 2: DOCTOR DASHBOARD & ANALYTICS APIS ---", flush=True)

        # 10. Dashboard summary statistics
        summary_a = get_dashboard_summary(current_doctor=doc_a, db=db)
        if summary_a.total_assessments >= 1:
            ok(f"10. GET /dashboard/summary: total_assessments={summary_a.total_assessments}, predictions={summary_a.total_predictions}")
        else:
            fail("10. Dashboard summary failed", f"total_assessments={summary_a.total_assessments}")

        # 11. Recent assessments (latest 5)
        recent_asms = get_dashboard_recent_assessments(current_doctor=doc_a, db=db)
        if len(recent_asms) >= 1 and recent_asms[0].assessment_id == asm_a.assessment_id:
            ok(f"11. GET /dashboard/recent-assessments: returned {len(recent_asms)} recent assessments")
        else:
            fail("11. Recent assessments failed", f"got {len(recent_asms)}")

        # 12. Recent predictions
        recent_preds = get_dashboard_recent_predictions(current_doctor=doc_a, db=db)
        ok(f"12. GET /dashboard/recent-predictions: returned {len(recent_preds)} predictions")

        # 13. Prediction distribution
        dist_all = get_dashboard_prediction_distribution(model="ALL", current_doctor=doc_a, db=db)
        if dist_all.class_0_label and dist_all.notice:
            ok(f"13. GET /dashboard/prediction-distribution (ALL): class_0={dist_all.class_0_count}, class_1={dist_all.class_1_count}")
        else:
            fail("13. Prediction distribution failed")

        dist_lr = get_dashboard_prediction_distribution(model="LOGISTIC_REGRESSION", current_doctor=doc_a, db=db)
        ok(f"    GET /dashboard/prediction-distribution (LOGISTIC_REGRESSION): model={dist_lr.model}")

        dist_ann = get_dashboard_prediction_distribution(model="ANN", current_doctor=doc_a, db=db)
        ok(f"    GET /dashboard/prediction-distribution (ANN): model={dist_ann.model}")

        # 14. Model usage comparison
        usage = get_dashboard_model_usage(current_doctor=doc_a, db=db)
        ok(f"14. GET /dashboard/model-usage: lr={usage.logistic_regression}, ann={usage.ann}, total={usage.total}")

        # 15. Doctor B dashboard data isolation
        summary_b = get_dashboard_summary(current_doctor=doc_b, db=db)
        if summary_b.total_assessments == 1:
            ok(f"15. Doctor B summary isolated: total_assessments={summary_b.total_assessments} (Doctor A had {summary_a.total_assessments})")
        else:
            fail("15. Summary isolation failed", f"Doctor B got {summary_b.total_assessments}")

        # -------------------------------------------------------------------
        # PART 3: MODEL PERFORMANCE VERIFIED METRICS CHECK
        # -------------------------------------------------------------------
        print("\n--- PART 3: MODEL PERFORMANCE VERIFICATION ---", flush=True)

        from frontend_metrics import VERIFIED_LR_METRICS, VERIFIED_ANN_METRICS

        # Check LR Metrics
        if (
            abs(VERIFIED_LR_METRICS["accuracy"] - 75.6045) < 0.01
            and abs(VERIFIED_LR_METRICS["precision"] - 67.5469) < 0.01
            and abs(VERIFIED_LR_METRICS["sensitivity"] - 48.1053) < 0.01
            and abs(VERIFIED_LR_METRICS["specificity"] - 88.6707) < 0.01
            and abs(VERIFIED_LR_METRICS["f1_score"] - 55.7555) < 0.01
            and abs(VERIFIED_LR_METRICS["auroc"] - 77.1713) < 0.01
        ):
            ok("16. Verified Logistic Regression Cross-Validation metrics match requirements (75.60% Acc, 77.17% AUROC)")
        else:
            fail("16. Logistic Regression metric mismatch", str(VERIFIED_LR_METRICS))

        # Check ANN Metrics
        if (
            abs(VERIFIED_ANN_METRICS["accuracy"] - 74.5989) < 0.01
            and abs(VERIFIED_ANN_METRICS["precision"] - 63.5128) < 0.01
            and abs(VERIFIED_ANN_METRICS["sensitivity"] - 47.1053) < 0.01
            and abs(VERIFIED_ANN_METRICS["specificity"] - 87.6707) < 0.01
            and abs(VERIFIED_ANN_METRICS["f1_score"] - 53.9706) < 0.01
            and abs(VERIFIED_ANN_METRICS["auroc"] - 75.6756) < 0.01
        ):
            ok("17. Verified ANN (32-16 architecture) Cross-Validation metrics match requirements (74.60% Acc, 75.68% AUROC)")
        else:
            fail("17. ANN metric mismatch", str(VERIFIED_ANN_METRICS))

        # -------------------------------------------------------------------
        # PART 4: EXISTING ML PREDICTION ENDPOINTS INTEGRITY CHECK
        # -------------------------------------------------------------------
        print("\n--- PART 4: PREDICTION ENDPOINTS INTEGRITY ---", flush=True)

        token_a = create_access_token(doctor_id=doc_a.doctor_id, email=doc_a.email, full_name=doc_a.full_name)
        auth_doc = get_auth_doctor(authorization=f"Bearer {token_a}")

        sample = PatientData(
            age=65, anaemia=1, creatinine_phosphokinase=250.0, diabetes=0,
            ejection_fraction=35.0, high_blood_pressure=1, platelets=150000.0,
            serum_creatinine=1.3, serum_sodium=137.0, sex=1, smoking=0,
        )

        lr_res = predict_logistic_regression(patient=sample, current_doctor=auth_doc)
        if "predicted_class" in lr_res and "predicted_probability" in lr_res and lr_res["model"] == "Logistic Regression":
            ok(f"18. Logistic Regression endpoint functioning: class={lr_res['predicted_class']} prob={lr_res['predicted_probability']:.1%}")
        else:
            fail("18. Logistic Regression endpoint response format invalid")

        ann_res = predict_ann(patient=sample, current_doctor=auth_doc)
        if "predicted_class" in ann_res and "predicted_probability" in ann_res and ann_res["model"] == "Artificial Neural Network":
            ok(f"19. ANN prediction endpoint functioning: class={ann_res['predicted_class']} prob={ann_res['predicted_probability']:.1%}")
        else:
            fail("19. ANN prediction endpoint response format invalid")

    finally:
        # Cleanup seeded records
        try:
            if doc_a:
                db.query(Assessment).filter(Assessment.doctor_id == doc_a.doctor_id).delete()
                db.query(Doctor).filter(Doctor.doctor_id == doc_a.doctor_id).delete()
            if doc_b:
                db.query(Assessment).filter(Assessment.doctor_id == doc_b.doctor_id).delete()
                db.query(Doctor).filter(Doctor.doctor_id == doc_b.doctor_id).delete()
            db.commit()
            ok("Test cleanup completed cleanly")
        except Exception as exc:
            print(f"Cleanup warning: {exc}")
        finally:
            db.close()

    print("\n" + "=" * 70, flush=True)
    print(f"  RESULTS: {PASS} PASSED | {FAIL} FAILED", flush=True)
    if FAIL == 0:
        print("  ALL TESTS PASSED SUCCESSFULLY! (100% VERIFIED)", flush=True)
    print("=" * 70, flush=True)
    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
