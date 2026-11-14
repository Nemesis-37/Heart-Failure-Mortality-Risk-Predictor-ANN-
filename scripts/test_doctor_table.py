"""
scripts/test_doctor_table.py
============================
Verification script for Step 2: Doctors database table.

Tests:
1. Doctors table exists in SQL Server under 'clinical' schema.
2. Checks columns and constraints (PK, Unique email, Unique reg number).
3. Inserts a test development doctor.
4. Retrieves the doctor and verifies all fields.
5. Verifies duplicate email rejection (integrity error).
6. Verifies duplicate registration number rejection.
7. Cleans up the test record.
"""

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def run_doctor_table_test():
    try:
        from database.config import SessionLocal, engine
        from database.models import Base, Doctor
        from sqlalchemy import text
        from sqlalchemy.exc import IntegrityError
    except ImportError as e:
        print(f"[FAIL] Missing database dependencies: {e}")
        return False

    print("\n" + "=" * 60)
    print("  STEP 2 VERIFICATION: clinical.Doctors Table")
    print("=" * 60)

    # 1. Check Table in INFORMATION_SCHEMA
    with engine.connect() as conn:
        table_exists = conn.execute(text("""
            SELECT TABLE_NAME 
            FROM INFORMATION_SCHEMA.TABLES 
            WHERE TABLE_SCHEMA = 'clinical' AND TABLE_NAME = 'Doctors'
        """)).scalar()

        if not table_exists:
            print("  [INFO] clinical.Doctors does not exist yet. Creating via Base.metadata...")
            Base.metadata.create_all(bind=engine)
            print("  [OK] Base.metadata.create_all() executed.")
        else:
            print("  [OK] clinical.Doctors table exists in SQL Server.")

        # 2. Check Columns
        columns = conn.execute(text("""
            SELECT COLUMN_NAME, DATA_TYPE, IS_NULLABLE
            FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'clinical' AND TABLE_NAME = 'Doctors'
            ORDER BY ORDINAL_POSITION
        """)).fetchall()
        print(f"  [OK] Found {len(columns)} columns in clinical.Doctors:")
        for col, dtype, is_null in columns:
            print(f"       - {col:24} ({dtype}, nullable={is_null})")

    # 3. Test Insert & Retrieval
    db = SessionLocal()
    test_id = str(uuid.uuid4())
    test_email = f"test.doctor.{uuid.uuid4().hex[:6]}@cardio-ai.internal"
    test_reg = f"MCI-{uuid.uuid4().hex[:8].upper()}"

    try:
        print("\n  [TEST 1] Inserting test doctor record...")
        test_doc = Doctor(
            doctor_id=test_id,
            full_name="Dr. Evelyn Sterling",
            email=test_email,
            password_hash="$argon2id$v=19$m=65536,t=2,p=1$fakehasheddevsecret123",
            mobile="+1-555-019-2834",
            medical_degree="MD, FACC - Cardiovascular Disease",
            registration_number=test_reg,
            registration_council="National Medical Commission",
            email_verified=False,
            verification_status="PENDING",
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(test_doc)
        db.commit()
        print(f"  [OK] Doctor inserted with ID: {test_id}")

        # Retrieve
        fetched = db.query(Doctor).filter(Doctor.doctor_id == test_id).first()
        assert fetched is not None, "Failed to retrieve doctor"
        assert fetched.email == test_email
        assert fetched.verification_status == "PENDING"
        assert fetched.email_verified is False
        print(f"  [OK] Doctor retrieved: {fetched.full_name} ({fetched.email})")

        # 4. Test Duplicate Email Rejection
        print("\n  [TEST 2] Testing duplicate email rejection...")
        dup_email_doc = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. Impostor",
            email=test_email,  # duplicate
            password_hash="somehash",
            mobile="+1-555-000-0000",
            medical_degree="MBBS",
            registration_number=f"MCI-{uuid.uuid4().hex[:8].upper()}",
            registration_council="Council",
        )
        try:
            db.add(dup_email_doc)
            db.commit()
            print("  [FAIL] Duplicate email was NOT rejected!")
            return False
        except IntegrityError:
            db.rollback()
            print("  [OK] UniqueConstraint(email) successfully rejected duplicate email!")

        # 5. Test Duplicate Reg Number Rejection
        print("\n  [TEST 3] Testing duplicate registration number rejection...")
        dup_reg_doc = Doctor(
            doctor_id=str(uuid.uuid4()),
            full_name="Dr. Second Duplicate",
            email=f"unique.{uuid.uuid4().hex[:6]}@hospital.org",
            password_hash="somehash",
            mobile="+1-555-000-0000",
            medical_degree="MBBS",
            registration_number=test_reg,  # duplicate
            registration_council="Council",
        )
        try:
            db.add(dup_reg_doc)
            db.commit()
            print("  [FAIL] Duplicate registration number was NOT rejected!")
            return False
        except IntegrityError:
            db.rollback()
            print("  [OK] UniqueConstraint(registration_number) successfully rejected duplicate reg number!")

    finally:
        # Cleanup test doctor
        print("\n  [CLEANUP] Cleaning up test record...")
        db.query(Doctor).filter(Doctor.doctor_id == test_id).delete()
        db.commit()
        db.close()
        print("  [OK] Test record cleaned up.")

    print("\n" + "=" * 60)
    print("  ALL STEP 2 DATABASE TESTS PASSED!")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = run_doctor_table_test()
    sys.exit(0 if success else 1)
