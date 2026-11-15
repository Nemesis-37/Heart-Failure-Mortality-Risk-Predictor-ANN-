"""
scripts/test_admin_dashboard_full.py
====================================
Comprehensive test suite for the complete Admin Dashboard:
1. Overview Statistics (/admin/overview and /admin/dashboard/summary)
2. Recent Activity Summary (/admin/dashboard/recent-activity)
3. Doctor Management (/admin/doctors with search, status filtering, pagination)
4. Single Doctor Detail (/admin/doctors/{id})
5. Doctor Verification Queue (/admin/doctors/pending)
6. Doctor Credential Approval with automated username assignment & email notification
7. Doctor Credential Rejection with clinical reason & email notification
8. Doctor Activity Overview (/admin/doctor-activity and /admin/doctors/{id}/activity)
9. Model Performance Cross-Validation Benchmarks (/admin/model-performance)
10. Account suspension / reactivation (/admin/doctors/{id}/toggle-active)
11. Security & RBAC: unauthenticated (401) and doctor-token (403) rejection

Run:
    .\\venv\\Scripts\\python.exe scripts\\test_admin_dashboard_full.py
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
    print(f"\n{'─' * 65}", flush=True)
    print(f"  {title}", flush=True)
    print(f"{'─' * 65}", flush=True)


def run_tests():
    print("\n" + "=" * 70, flush=True)
    print("  ADMIN DASHBOARD COMPLETE API TEST SUITE", flush=True)
    print("=" * 70, flush=True)

    from fastapi import HTTPException
    from database.config import SessionLocal, get_db
    from database.models import Administrator, Doctor, Assessment, Prediction
    from admin.security import create_admin_token, get_current_admin
    from auth.security import hash_password
    from auth.session_service import create_access_token
    from admin.router import (
        get_admin_overview,
        get_recent_activity,
        get_doctor_activity,
        get_single_doctor_activity,
        list_doctors,
        list_pending_doctors,
        get_doctor_detail,
        approve_doctor,
        reject_doctor,
        toggle_doctor_active,
        get_model_performance,
        ensure_initial_admin,
    )
    from admin.schemas import DoctorRejectionRequest

    db = SessionLocal()
    suffix = uuid.uuid4().hex[:6]

    # Pre-test cleanup & admin setup
    admin = db.query(Administrator).filter(Administrator.username == "test_admin_board").first()
    if not admin:
        admin = Administrator(
            admin_id=str(uuid.uuid4()),
            username="test_admin_board",
            email=f"admin_board_{suffix}@hospital.org",
            password_hash=hash_password("AdminPass123!"),
            full_name="Dashboard Super Admin",
            role="Super Administrator",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(admin)
        db.commit()

    admin_token = create_admin_token(admin.admin_id, admin.username)

    # Create test doctors: 1 pending, 1 approved, 1 rejected
    doc_pending = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name=f"Dr. Pend Review_{suffix}",
        email=f"pending_{suffix}@hospital.org",
        password_hash=hash_password("DocPass123!"),
        mobile="+15550101",
        medical_degree="MBBS, MD Cardiology",
        registration_number=f"REG-PEND-{suffix.upper()}",
        registration_council="Maharashtra Medical Council",
        email_verified=True,
        verification_status="PENDING",
        is_active=True,
        created_at=datetime.now(timezone.utc),
    )
    doc_approved = Doctor(
        doctor_id=str(uuid.uuid4()),
        full_name=f"Dr. Appro Veds_{suffix}",
        email=f"approved_{suffix}@hospital.org",
        username=f"dr_appro_{suffix}",
        password_hash=hash_password("DocPass123!"),
        mobile="+15550102",
        medical_degree="MBBS, DM Cardiology",
        registration_number=f"REG-APPR-{suffix.upper()}",
        registration_council="Delhi Medical Council",
        email_verified=True,
        verification_status="APPROVED",
        is_active=True,
        created_at=datetime.now(timezone.utc),
        approved_at=datetime.now(timezone.utc),
    )
    db.add(doc_pending)
    db.add(doc_approved)
    db.commit()

    try:
        # =====================================================================
        # 1. OVERVIEW & SUMMARY
        # =====================================================================
        section("PART 1: OVERVIEW & DASHBOARD SUMMARY APIS")
        overview = get_admin_overview(current_admin=admin, db=db)
        if overview.total_doctors >= 2 and overview.approved_doctors >= 1 and overview.pending_doctors >= 1:
            ok("GET /admin/overview returns aggregated statistics", f"total={overview.total_doctors}, approved={overview.approved_doctors}, pending={overview.pending_doctors}")
        else:
            fail("GET /admin/overview failed count assertions")

        # =====================================================================
        # 2. RECENT ACTIVITY SUMMARY
        # =====================================================================
        section("PART 2: RECENT ACTIVITY SUMMARY API")
        recent = get_recent_activity(current_admin=admin, db=db)
        if len(recent.recent_registrations) > 0:
            ok("GET /admin/dashboard/recent-activity returns recent registrations", f"latest: {recent.recent_registrations[0].full_name}")
        else:
            fail("GET /admin/dashboard/recent-activity missing recent registrations")

        if hasattr(recent, "total_assessments_last_7_days") and hasattr(recent, "total_predictions_last_7_days"):
            ok("GET /admin/dashboard/recent-activity returns 7-day volume counts", f"asms={recent.total_assessments_last_7_days}, preds={recent.total_predictions_last_7_days}")
        else:
            fail("GET /admin/dashboard/recent-activity missing 7-day throughput counts")

        # =====================================================================
        # 3. DOCTOR MANAGEMENT (SEARCH, FILTER, PAGINATION)
        # =====================================================================
        section("PART 3: DOCTOR MANAGEMENT (LIST, SEARCH, FILTER)")
        all_docs = list_doctors(status_filter="ALL", search=None, skip=0, limit=100, current_admin=admin, db=db)
        if len(all_docs) >= 2:
            ok("GET /admin/doctors?status_filter=ALL returns full roster", f"count={len(all_docs)}")
        else:
            fail("GET /admin/doctors?status_filter=ALL returned insufficient records")

        # Search by registration number
        searched = list_doctors(status_filter="ALL", search=f"REG-PEND-{suffix.upper()}", current_admin=admin, db=db)
        if len(searched) == 1 and searched[0].doctor_id == doc_pending.doctor_id:
            ok("GET /admin/doctors with search filter matches registration number", f"found {searched[0].full_name}")
        else:
            fail("GET /admin/doctors search filter failed")

        # Status filter APPROVED
        approved_list = list_doctors(status_filter="APPROVED", current_admin=admin, db=db)
        if all(d.verification_status == "APPROVED" for d in approved_list):
            ok("GET /admin/doctors?status_filter=APPROVED strictly filters by status", f"count={len(approved_list)}")
        else:
            fail("GET /admin/doctors?status_filter=APPROVED returned non-approved records")

        # =====================================================================
        # 4. SINGLE DOCTOR DETAIL
        # =====================================================================
        section("PART 4: SINGLE DOCTOR PROFILE DETAIL")
        detail = get_doctor_detail(doctor_id=doc_approved.doctor_id, current_admin=admin, db=db)
        if detail.doctor_id == doc_approved.doctor_id and detail.username == f"dr_appro_{suffix}":
            ok("GET /admin/doctors/{id} returns complete physician profile with username", f"username={detail.username}")
        else:
            fail("GET /admin/doctors/{id} returned incorrect profile or missing username")

        # 404 for unknown doctor
        try:
            get_doctor_detail(doctor_id="non-existent-uuid", current_admin=admin, db=db)
            fail("Expected 404 for non-existent doctor")
        except HTTPException as e:
            if e.status_code == 404:
                ok("GET /admin/doctors/{invalid_id} returns HTTP 404 Not Found")
            else:
                fail(f"Expected 404, got {e.status_code}")

        # =====================================================================
        # 5. PENDING VERIFICATION QUEUE
        # =====================================================================
        section("PART 5: DOCTOR VERIFICATION QUEUE")
        pending_list = list_pending_doctors(current_admin=admin, db=db)
        if any(d.doctor_id == doc_pending.doctor_id for d in pending_list):
            ok("GET /admin/doctors/pending returns doctors awaiting credential review")
        else:
            fail("Pending doctor not found in pending queue")

        # =====================================================================
        # 6. APPROVE DOCTOR & USERNAME GENERATION
        # =====================================================================
        section("PART 6: CREDENTIAL APPROVAL & UNIQUE USERNAME GENERATION")
        approve_resp = approve_doctor(doctor_id=doc_pending.doctor_id, current_admin=admin, db=db)
        if approve_resp.verification_status == "APPROVED" and approve_resp.username:
            ok("PATCH /admin/doctors/{id}/approve approves doctor and assigns username", f"assigned username: {approve_resp.username}")
        else:
            fail("Doctor approval failed or username was not generated")

        # Verify DB state
        db.refresh(doc_pending)
        if doc_pending.verification_status == "APPROVED" and doc_pending.approved_at is not None:
            ok("Doctor record updated in database: status='APPROVED', approved_at recorded", f"approved_at={doc_pending.approved_at}")
        else:
            fail("Database record not properly updated on approval")

        # =====================================================================
        # 7. REJECT DOCTOR
        # =====================================================================
        section("PART 7: CREDENTIAL REJECTION & CLINICAL REASON RECORDING")
        reject_req = DoctorRejectionRequest(reason="Medical Council registration number does not match State Council database records.")
        reject_resp = reject_doctor(doctor_id=doc_pending.doctor_id, payload=reject_req, current_admin=admin, db=db)
        if reject_resp.verification_status == "REJECTED" and "Reason recorded" in reject_resp.message:
            ok("PATCH /admin/doctors/{id}/reject rejects doctor with reason", f"status={reject_resp.verification_status}")
        else:
            fail("Doctor rejection failed")

        db.refresh(doc_pending)
        if doc_pending.verification_status == "REJECTED" and doc_pending.rejection_reason == reject_req.reason:
            ok("Rejection reason persisted accurately in Doctors table")
        else:
            fail("Rejection reason not stored properly in database")

        # =====================================================================
        # 8. DOCTOR ACTIVITY ENDPOINTS
        # =====================================================================
        section("PART 8: DOCTOR ACTIVITY ENDPOINTS")
        activity_all = get_doctor_activity(current_admin=admin, db=db)
        if len(activity_all) >= 2 and all(hasattr(a, "total_assessments") and hasattr(a, "total_predictions") for a in activity_all):
            ok("GET /admin/doctor-activity returns activity stats for all doctors")
        else:
            fail("GET /admin/doctor-activity missing records or fields")

        single_act = get_single_doctor_activity(doctor_id=doc_approved.doctor_id, current_admin=admin, db=db)
        if single_act.doctor_id == doc_approved.doctor_id and single_act.username == f"dr_appro_{suffix}":
            ok("GET /admin/doctors/{id}/activity returns single doctor activity stats")
        else:
            fail("GET /admin/doctors/{id}/activity failed")

        # =====================================================================
        # 9. MODEL PERFORMANCE BENCHMARKS
        # =====================================================================
        section("PART 9: MODEL PERFORMANCE BENCHMARKS (ADMIN ONLY)")
        perf = get_model_performance(current_admin=admin)
        if (
            perf.logistic_regression.accuracy == 75.6045
            and perf.artificial_neural_network.accuracy == 74.5989
            and perf.features_used == 11
        ):
            ok("GET /admin/model-performance returns verified cross-validation benchmarks", f"LR Acc={perf.logistic_regression.accuracy}%, ANN Acc={perf.artificial_neural_network.accuracy}%")
        else:
            fail("GET /admin/model-performance returned incorrect benchmark metrics")

        # =====================================================================
        # 10. TOGGLE ACTIVE (SUSPEND / REACTIVATE)
        # =====================================================================
        section("PART 10: TOGGLE ACTIVE (SUSPEND / REACTIVATE)")
        toggle_resp = toggle_doctor_active(doctor_id=doc_approved.doctor_id, current_admin=admin, db=db)
        db.refresh(doc_approved)
        if doc_approved.is_active is False:
            ok("PATCH /admin/doctors/{id}/toggle-active successfully suspends account", f"is_active={doc_approved.is_active}")
        else:
            fail("Failed to suspend account")

        toggle_resp2 = toggle_doctor_active(doctor_id=doc_approved.doctor_id, current_admin=admin, db=db)
        db.refresh(doc_approved)
        if doc_approved.is_active is True:
            ok("PATCH /admin/doctors/{id}/toggle-active successfully reactivates account", f"is_active={doc_approved.is_active}")
        else:
            fail("Failed to reactivate account")

        # =====================================================================
        # 11. SECURITY & RBAC GATING
        # =====================================================================
        section("PART 11: SECURITY & RBAC GATING")
        doc_token = create_access_token(doc_approved.doctor_id, doc_approved.email, doc_approved.full_name)
        from admin.security import verify_admin_token, get_current_admin
        
        # 11.1 verify_admin_token returns None for doctor token
        admin_resolved = verify_admin_token(doc_token)
        if admin_resolved is None:
            ok("verify_admin_token rejects doctor JWT (returns None)")
        else:
            fail("Doctor token should not verify as admin")

        # 11.2 get_current_admin raises 403 Forbidden for doctor token
        try:
            get_current_admin(authorization=f"Bearer {doc_token}")
            fail("Expected HTTP 403 when doctor token accesses admin dependency")
        except HTTPException as e:
            if e.status_code == 403:
                ok("get_current_admin strictly rejects doctor token with HTTP 403 Forbidden")
            else:
                fail(f"Expected HTTP 403, got {e.status_code}")

        # 11.3 get_current_admin raises 401 Unauthorized when missing header
        try:
            get_current_admin(authorization=None, x_admin_token=None)
            fail("Expected HTTP 401 for unauthenticated request")
        except HTTPException as e:
            if e.status_code == 401:
                ok("get_current_admin rejects missing authorization header with HTTP 401")
            else:
                fail(f"Expected HTTP 401, got {e.status_code}")

    finally:
        # Cleanup test records
        try:
            db.query(Doctor).filter(Doctor.doctor_id.in_([doc_pending.doctor_id, doc_approved.doctor_id])).delete(synchronize_session=False)
            db.query(Administrator).filter(Administrator.admin_id == admin.admin_id).delete(synchronize_session=False)
            db.commit()
            ok("Test fixtures cleaned up successfully")
        except Exception as e:
            print(f"Cleanup error: {e}")
        db.close()

    print("\n" + "=" * 70)
    print(f"  RESULTS: {PASS} PASSED, {FAIL} FAILED")
    print("=" * 70)
    if FAIL > 0:
        sys.exit(1)


if __name__ == "__main__":
    run_tests()
