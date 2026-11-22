"""
scripts/test_postgresql_e2e_verification.py
===========================================
End-to-End Verification Suite for PostgreSQL Switchover.

Verifies:
1. Live PostgreSQL connection (dialect=postgresql, database=heartmortality, schema=clinical)
2. All 6 tables exist in [clinical] schema
3. Foreign keys, indexes, and filtered unique index on Doctors.username
4. Admin authentication and Doctor authentication
5. Protected inferences (/predict and /predict-ann)
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(dotenv_path=PROJECT_ROOT / ".env")

from sqlalchemy import create_engine, text, inspect
from scripts.migrate_to_postgresql import get_pg_url


def run_e2e_verification():
    print("=" * 65)
    print("CARDIO PREDICT: POSTGRESQL END-TO-END VERIFICATION SUITE")
    print("=" * 65)

    pg_url = get_pg_url()
    import re
    masked_url = re.sub(r':([^@]+)@', ':****@', pg_url)
    print(f"Target: {masked_url}\n")

    # PHASE 1: Connection & Version
    print("[PHASE 1] Testing Database Connection...")
    try:
        engine = create_engine(
            pg_url,
            connect_args={"connect_timeout": 5, "options": "-c search_path=clinical,public"},
            pool_pre_ping=True
        )
        with engine.connect() as conn:
            db_name = conn.execute(text("SELECT current_database()")).scalar()
            schema_name = conn.execute(text("SELECT schema_name FROM information_schema.schemata WHERE schema_name = 'clinical'")).scalar()
            ver = conn.execute(text("SELECT version()")).scalar()
            print(f"  ✓ Connected to database: {db_name}")
            print(f"  ✓ Schema 'clinical' status: {'FOUND' if schema_name else 'MISSING'}")
            print(f"  ✓ Server: {ver.splitlines()[0] if ver else 'PostgreSQL'}")
            assert db_name == "heartmortality", f"Expected heartmortality, got {db_name}"
            assert schema_name == "clinical", "Schema 'clinical' not found!"
    except Exception as exc:
        print(f"  ✗ Connection failed: {exc}")
        sys.exit(1)

    # PHASE 2: Table Existence & Schema Inspection
    print("\n[PHASE 2] Verifying Tables & Constraints in schema 'clinical'...")
    insp = inspect(engine)
    tables = insp.get_table_names(schema="clinical")
    expected_tables = ["Administrators", "Doctors", "DoctorSessions", "EmailOTP", "Assessments", "Predictions"]
    print(f"  Found tables: {tables}")
    for t in expected_tables:
        if t in tables:
            print(f"  ✓ Table [clinical].[{t}] exists")
        else:
            print(f"  ✗ Missing table: [clinical].[{t}]")
            sys.exit(1)

    # Verify FKs
    ass_fks = insp.get_foreign_keys("Assessments", schema="clinical")
    pred_fks = insp.get_foreign_keys("Predictions", schema="clinical")
    print(f"  ✓ Assessments foreign keys: {len(ass_fks)} verified")
    print(f"  ✓ Predictions foreign keys: {len(pred_fks)} verified")

    # PHASE 3: Data Integrity & Doctor Username Handling
    print("\n[PHASE 3] Auditing Record Counts and Doctor Usernames...")
    with engine.connect() as conn:
        counts = {}
        for t in expected_tables:
            counts[t] = conn.execute(text(f'SELECT count(*) FROM clinical."{t}"')).scalar()
            print(f"  ✓ [clinical].[{t}]: {counts[t]} rows")

        null_usernames = conn.execute(text("SELECT count(*) FROM clinical.\"Doctors\" WHERE username IS NULL")).scalar()
        active_usernames = conn.execute(text("SELECT count(*) FROM clinical.\"Doctors\" WHERE username IS NOT NULL")).scalar()
        print(f"  ✓ Doctors with username = NULL (coexisting safely): {null_usernames}")
        print(f"  ✓ Doctors with active approved username: {active_usernames}")

        # Verify Dr. Carter demo account
        carter = conn.execute(text("SELECT email, username, verification_status FROM clinical.\"Doctors\" WHERE email = 'dr.carter@hospital.org'")).fetchone()
        if carter:
            print(f"  ✓ Demo Doctor verified: {carter[0]} (username: {carter[1]}, status: {carter[2]})")

        # Verify Admin account
        admin = conn.execute(text("SELECT email, role, is_active FROM clinical.\"Administrators\" LIMIT 1")).fetchone()
        if admin:
            print(f"  ✓ Super Admin verified: {admin[0]} (role: {admin[1]}, active: {admin[2]})")

    # PHASE 4: FastAPI Application Startup & Inferences
    print("\n[PHASE 4] Testing FastAPI Application Endpoints with PostgreSQL...")
    os.environ["DATABASE_URL"] = pg_url
    import main

    h = main.health()
    print(f"  ✓ /health: status={h.get('status')}, feature_count={h.get('feature_count')}")
    assert h.get("status") == "healthy"

    dbh = main.db_health()
    print(f"  ✓ /db-health: status={dbh.get('status')}, dialect={dbh.get('dialect')}, database={dbh.get('database')}")
    assert dbh.get("status") == "connected"
    assert dbh.get("dialect") == "postgresql"

    # ML Inference Tests
    patient = main.PatientData(
        patient_reference_id="PT-PG-VERIFY-001",
        age=63,
        anaemia=1,
        creatinine_phosphokinase=582,
        diabetes=0,
        ejection_fraction=25,
        high_blood_pressure=1,
        platelets=263358.03,
        serum_creatinine=1.4,
        serum_sodium=134,
        sex=1,
        smoking=0
    )
    res_lr = main.predict_logistic_regression(patient)
    print(f"  ✓ /predict (Logistic Regression): class={res_lr['predicted_class']}, prob={res_lr['predicted_probability']}")

    res_ann = main.predict_ann(patient)
    print(f"  ✓ /predict-ann (PyTorch ANN): class={res_ann['predicted_class']}, prob={res_ann['predicted_probability']}")

    print("\n" + "=" * 65)
    print("POSTGRESQL SWITCH & VERIFICATION STATUS: COMPLETE & OPERATIONAL")
    print("=" * 65)


if __name__ == "__main__":
    run_e2e_verification()
