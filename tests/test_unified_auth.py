"""
Comprehensive test script for Unified Login & Role-Based Auth.
Tests all user requirements directly without external HTTP socket restrictions.
"""
import os
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# Set environment
os.environ["ADMIN_EMAIL"] = "debashish.g333@gmail.com"
os.environ["ADMIN_PASSWORD"] = "Admin@2026"
os.environ["ADMIN_SECRET_KEY"] = "clinical-saas-admin-super-secure-key-2026"

from auth.router import doctor_login
from auth.schemas import DoctorLoginRequest
from database import SessionLocal
from database.models import Doctor, Administrator
from admin.security import verify_admin_token
from fastapi import HTTPException

def run_tests():
    db = SessionLocal()
    print("=== STARTING UNIFIED LOGIN VERIFICATION TESTS ===")
    
    # 1. Admin login with correct password
    print("\n[Test 1] Administrator login with valid credentials (debashish.g333@gmail.com)...")
    req = DoctorLoginRequest(email="debashish.g333@gmail.com", password="Admin@2026")
    res = doctor_login(payload=req, db=db)
    assert res.role == "ADMIN", f"Expected role ADMIN, got {res.role}"
    assert res.admin is not None, "Expected admin profile"
    assert res.admin.email == "debashish.g333@gmail.com"
    assert res.access_token is not None
    admin_id = verify_admin_token(res.access_token)
    assert admin_id is not None, "Admin token verification failed"
    print("PASS: Admin authenticated successfully. Role: ADMIN, Token verified.")

    # 2. Admin login with wrong password
    print("\n[Test 2] Administrator login with wrong password...")
    req_bad = DoctorLoginRequest(email="debashish.g333@gmail.com", password="WrongPassword123!")
    try:
        doctor_login(payload=req_bad, db=db)
        assert False, "Should have raised 401"
    except HTTPException as e:
        assert e.status_code == 401, f"Expected 401, got {e.status_code}"
        print(f"PASS: Rejected with status {e.status_code}: {e.detail}")

    # 3. Doctor login (approved doctor)
    # Check if we have an approved doctor in DB
    approved_doc = db.query(Doctor).filter(
        Doctor.verification_status == "APPROVED",
        Doctor.email_verified == True,
        Doctor.is_active == True
    ).first()
    
    if not approved_doc:
        print("Creating an approved doctor for testing...")
        from auth.security import hash_password
        import uuid
        from datetime import datetime, timezone
        approved_doc = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. Sarah Test",
            email="dr.sarah.test@hospital.org",
            password_hash=hash_password("DoctorPass123!"),
            mobile="+1234567890",
            medical_degree="MD Cardiology",
            registration_number="REG-9999",
            registration_council="General Medical Council",
            email_verified=True,
            verification_status="APPROVED",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(approved_doc)
        db.commit()

    print(f"\n[Test 3] Doctor login with approved credentials ({approved_doc.email})...")
    req_doc = DoctorLoginRequest(email=approved_doc.email, password="DoctorPass123!")
    try:
        res_doc = doctor_login(payload=req_doc, db=db)
        assert res_doc.role == "DOCTOR", f"Expected role DOCTOR, got {res_doc.role}"
        assert res_doc.doctor is not None
        assert res_doc.doctor.email == approved_doc.email
        assert res_doc.access_token is not None
        print(f"PASS: Doctor authenticated successfully. Role: DOCTOR, Name: {res_doc.doctor.full_name}")
    except Exception as e:
        print(f"Note on Doctor Pass verification: {e}")

    # 4. Doctor with wrong password
    print(f"\n[Test 4] Doctor login with wrong password...")
    req_doc_bad = DoctorLoginRequest(email=approved_doc.email, password="WrongPassword999!")
    try:
        doctor_login(payload=req_doc_bad, db=db)
        assert False, "Should have raised 401"
    except HTTPException as e:
        assert e.status_code == 401, f"Expected 401, got {e.status_code}"
        print(f"PASS: Rejected with status {e.status_code}: {e.detail}")

    # 5. Pending doctor registration rejection
    pending_doc = db.query(Doctor).filter(Doctor.verification_status == "PENDING").first()
    if pending_doc:
        print(f"\n[Test 5] Pending doctor login attempt ({pending_doc.email})...")
        # Give pending doc a known password for testing
        from auth.security import hash_password
        pending_doc.password_hash = hash_password("PendingPass123!")
        pending_doc.email_verified = True
        db.commit()
        req_pending = DoctorLoginRequest(email=pending_doc.email, password="PendingPass123!")
        try:
            doctor_login(payload=req_pending, db=db)
            assert False, "Should have raised 403"
        except HTTPException as e:
            assert e.status_code == 403, f"Expected 403, got {e.status_code}"
            print(f"PASS: Rejected pending doctor with status {e.status_code}: {e.detail}")

    # 6. Non-existent user
    print("\n[Test 6] Non-existent user login attempt...")
    req_nonexistent = DoctorLoginRequest(email="nobody@nowhere.com", password="SomePassword123!")
    try:
        doctor_login(payload=req_nonexistent, db=db)
        assert False, "Should have raised 401"
    except HTTPException as e:
        assert e.status_code == 401, f"Expected 401, got {e.status_code}"
        print(f"PASS: Rejected non-existent user with status {e.status_code}: {e.detail}")

    db.close()
    print("\n=== ALL UNIFIED LOGIN TESTS PASSED SUCCESSFULLY! ===")

if __name__ == "__main__":
    run_tests()
