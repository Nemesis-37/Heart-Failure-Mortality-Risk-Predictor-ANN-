"""
scripts/migrate_sqlite_to_sqlserver.py
======================================
Automated, idempotent data migration script from SQLite (clinical_local.db)
to Microsoft SQL Server (database: HeartMortalityPredictor, schema: [clinical]).

Fixes & Capabilities:
- Error A: Reconciles doctor_id data types (VARCHAR(64)) between Doctors and Assessments.
- Error B: Enforces strict schema creation sequence; DDL errors immediately halt migration.
- Error C: Implements a Filtered Unique Index on Doctors.username (allowing multiple NULLs).
- Full idempotency: safely updates existing records without unique constraint crashes.
- Row-count and foreign-key referential integrity verification.
- Preserves original SQLite database intact.
"""

import os
import sys
import sqlite3
import shutil
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

try:
    import pyodbc
except ImportError:
    print("[FATAL] pyodbc is not installed. Run: pip install pyodbc")
    sys.exit(1)

# Connection parameters
DB_SERVER = os.getenv("SERVER", os.getenv("DB_SERVER", r"DESKTOP-NA0D6N1\SQLEXPRESS")).strip()
DB_DATABASE = os.getenv("DATABASE", os.getenv("DB_NAME", os.getenv("DB_DATABASE", "HeartMortalityPredictor"))).strip()
DB_AUTH_MODE = os.getenv("DB_AUTH_MODE", "windows").lower().strip()
DB_USERNAME = os.getenv("DB_USERNAME", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
DB_DRIVER = os.getenv("DRIVER", os.getenv("DB_DRIVER", "{ODBC Driver 18 for SQL Server}")).strip("{}")

SQLITE_PATH = PROJECT_ROOT / "clinical_local.db"


def get_odbc_conn_str(database: str = "HeartMortalityPredictor") -> str:
    raw_env_str = os.getenv("DB_CONNECTION_STRING", "").strip("\"'")
    if raw_env_str:
        if database == "master":
            import re
            return re.sub(r"DATABASE=[^;]+;", "DATABASE=master;", raw_env_str, flags=re.IGNORECASE)
        return raw_env_str

    params = {
        "DRIVER": f"{{{DB_DRIVER}}}",
        "SERVER": DB_SERVER,
        "DATABASE": database,
        "Trusted_Connection": "yes" if DB_AUTH_MODE == "windows" else "no",
        "Encrypt": "yes",
        "TrustServerCertificate": "yes",
    }
    if DB_AUTH_MODE == "sql" and DB_USERNAME and DB_PASSWORD:
        params["UID"] = DB_USERNAME
        params["PWD"] = DB_PASSWORD

    return ";".join(f"{k}={v}" for k, v in params.items())


def backup_sqlite():
    """Ensure a safe backup of SQLite database exists before starting."""
    if not SQLITE_PATH.exists():
        print(f"[FATAL] Source SQLite database '{SQLITE_PATH}' not found!")
        sys.exit(1)

    backup_path = PROJECT_ROOT / f"clinical_local_backup_pre_migration_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
    if not any(PROJECT_ROOT.glob("clinical_local_pre_migration_backup*.db")):
        shutil.copy2(SQLITE_PATH, backup_path)
        print(f"✓ SQLite database backed up to: {backup_path.name}")
    else:
        print("✓ Verified existing pre-migration SQLite backups.")


def verify_connection():
    """Verify live connection to target database."""
    print(f"\nConnecting to SQL Server database '{DB_DATABASE}' on '{DB_SERVER}'...")
    conn_str = get_odbc_conn_str(DB_DATABASE)
    try:
        conn = pyodbc.connect(conn_str, autocommit=True, timeout=10)
    except Exception as e:
        print(f"[FATAL] Could not connect to SQL Server on '{DB_SERVER}': {e}")
        sys.exit(1)

    cur = conn.cursor()
    cur.execute("SELECT @@SERVERNAME, DB_NAME(), @@VERSION")
    row = cur.fetchone()
    print("✓ Live SQL Server connection verified!")
    print(f" - Server: {row[0]}")
    print(f" - Database: {row[1]}")
    print(f" - Engine: {row[2].splitlines()[0]}")
    conn.close()


def prepare_and_align_schema():
    """
    Ensure [clinical] schema exists, handle legacy incompatible tables,
    and apply DDL with exact matching data types.
    """
    print(f"\nAligning and verifying schema in '{DB_DATABASE}'...")
    conn = pyodbc.connect(get_odbc_conn_str(DB_DATABASE), autocommit=True)
    cur = conn.cursor()

    # 1. Ensure [clinical] schema exists
    cur.execute("IF NOT EXISTS (SELECT * FROM sys.schemas WHERE name = 'clinical') EXEC('CREATE SCHEMA [clinical]')")

    # 2. Inspect clinical.Doctors if it already exists
    cur.execute("""
        SELECT DATA_TYPE, CHARACTER_MAXIMUM_LENGTH
        FROM INFORMATION_SCHEMA.COLUMNS
        WHERE TABLE_SCHEMA = 'clinical' AND TABLE_NAME = 'Doctors' AND COLUMN_NAME = 'doctor_id'
    """)
    doc_pk_info = cur.fetchone()
    if doc_pk_info:
        doc_id_type = doc_pk_info[0].upper()
        doc_id_len = doc_pk_info[1] or 64
        print(f"✓ Found existing [clinical].[Doctors] table. doctor_id column type is {doc_id_type}({doc_id_len})")
    else:
        doc_id_type = "VARCHAR"
        doc_id_len = 64

    # 3. Fix Error C: Drop any standard UQ_Doctors_Username constraint and replace with filtered unique index
    cur.execute("""
        IF EXISTS (SELECT * FROM sys.key_constraints WHERE name = 'UQ_Doctors_Username' AND parent_object_id = OBJECT_ID('[clinical].[Doctors]'))
        BEGIN
            ALTER TABLE [clinical].[Doctors] DROP CONSTRAINT [UQ_Doctors_Username];
        END
    """)
    cur.execute("""
        IF EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ_Doctors_Username' AND object_id = OBJECT_ID('[clinical].[Doctors]'))
        BEGIN
            DROP INDEX [UQ_Doctors_Username] ON [clinical].[Doctors];
        END
    """)
    cur.execute("""
        IF EXISTS (SELECT * FROM sys.objects WHERE object_id = OBJECT_ID(N'[clinical].[Doctors]') AND type in (N'U'))
        BEGIN
            IF NOT EXISTS (SELECT * FROM sys.indexes WHERE name = 'UQ_Doctors_Username' AND object_id = OBJECT_ID('[clinical].[Doctors]'))
            BEGIN
                CREATE UNIQUE NONCLUSTERED INDEX [UQ_Doctors_Username]
                ON [clinical].[Doctors] ([username])
                WHERE [username] IS NOT NULL;
            END
        END
    """)
    print("✓ Filtered unique index on Doctors.username verified (multiple NULLs supported).")

    # 4. Fix Error A & B: Detect and reconcile legacy/misaligned Assessments table
    cur.execute("""
        SELECT COUNT(*) FROM INFORMATION_SCHEMA.TABLES 
        WHERE TABLE_SCHEMA = 'clinical' AND TABLE_NAME = 'Assessments'
    """)
    has_assessments = cur.fetchone()[0] > 0

    if has_assessments:
        cur.execute("""
            SELECT COLUMN_NAME, DATA_TYPE FROM INFORMATION_SCHEMA.COLUMNS
            WHERE TABLE_SCHEMA = 'clinical' AND TABLE_NAME = 'Assessments'
        """)
        cols = {r[0].lower(): r[1].lower() for r in cur.fetchall()}
        recreate_assessments = False

        # Check required columns
        if 'id' not in cols or 'patient_reference_id' not in cols or 'assessment_code' not in cols:
            print("Notice: Existing [clinical].[Assessments] is missing required columns (id / patient_reference_id). Recreating...")
            recreate_assessments = True
        elif cols.get('doctor_id') != doc_id_type.lower():
            print(f"Notice: Existing [clinical].[Assessments].doctor_id ({cols.get('doctor_id')}) does not match Doctors.doctor_id ({doc_id_type}). Recreating...")
            recreate_assessments = True

        if recreate_assessments:
            cur.execute("DROP TABLE IF EXISTS [clinical].[Predictions]")
            cur.execute("DROP TABLE IF EXISTS [clinical].[Assessments]")

    # 5. Read and apply schema DDL from database/sql_server_assessments_schema.sql
    schema_file = PROJECT_ROOT / "database" / "sql_server_assessments_schema.sql"
    if not schema_file.exists():
        print(f"[FATAL] Schema file '{schema_file}' not found!")
        sys.exit(1)

    sql_content = schema_file.read_text(encoding="utf-8")
    batches = [b.strip() for b in sql_content.split("GO") if b.strip()]

    for i, batch in enumerate(batches, 1):
        try:
            cur.execute(batch)
        except Exception as b_err:
            err_msg = str(b_err)
            # Ignore harmless "already exists" notifications
            if "already exists" in err_msg.lower() or "there is already an object" in err_msg.lower():
                continue
            print(f"\n[FATAL DDL ERROR in Batch {i}]:\n{err_msg}\n")
            print("Failing SQL batch:")
            print(batch)
            conn.close()
            sys.exit(1)

    print("✓ All DDL schema batches applied and validated successfully.")
    conn.close()


def migrate_data():
    """Migrate all records from SQLite to SQL Server idempotently."""
    print(f"\nConnecting to SQLite database: {SQLITE_PATH}...")
    sq_conn = sqlite3.connect(str(SQLITE_PATH))
    sq_conn.row_factory = sqlite3.Row
    sq_cur = sq_conn.cursor()

    print(f"Connecting to SQL Server database: {DB_DATABASE}...")
    ms_conn = pyodbc.connect(get_odbc_conn_str(DB_DATABASE), autocommit=False)
    ms_cur = ms_conn.cursor()

    migration_order = [
        "Administrators",
        "Doctors",
        "DoctorSessions",
        "Assessments",
        "EmailOTP",
        "Predictions",
    ]

    report = {}

    for tbl in migration_order:
        try:
            sq_cur.execute(f"SELECT * FROM \"{tbl}\"")
            sq_rows = sq_cur.fetchall()
        except sqlite3.OperationalError:
            sq_rows = []

        sq_count = len(sq_rows)

        if sq_count == 0:
            ms_cur.execute(f"SELECT COUNT(*) FROM [clinical].[{tbl}]")
            ms_count = ms_cur.fetchone()[0]
            report[tbl] = {"sqlite": 0, "sql_server": ms_count, "inserted": 0, "updated_or_skipped": 0}
            print(f"Table [clinical].[{tbl}]: 0 rows in SQLite | Total in SQL Server={ms_count}")
            continue

        col_names = [col[0] for col in sq_cur.description]
        cols_joined = ", ".join(f"[{c}]" for c in col_names)
        placeholders = ", ".join("?" for _ in col_names)
        pk_col = col_names[0]

        insert_count = 0
        skip_count = 0

        for row in sq_rows:
            row_dict = dict(row)
            pk_val = row_dict[pk_col]

            # 1. Administrators: avoid UQ_Admin_Email violation by updating existing
            if tbl == "Administrators":
                ms_cur.execute(
                    "SELECT admin_id FROM [clinical].[Administrators] WHERE [admin_id] = ? OR [email] = ? OR [username] = ?",
                    (pk_val, row_dict.get("email"), row_dict.get("username")),
                )
                existing_admin = ms_cur.fetchone()
                if existing_admin:
                    ms_cur.execute(
                        """UPDATE [clinical].[Administrators]
                           SET [password_hash] = ?, [full_name] = ?, [role] = ?, [is_active] = 1
                           WHERE [admin_id] = ?""",
                        (row_dict.get("password_hash"), row_dict.get("full_name"), row_dict.get("role"), existing_admin[0]),
                    )
                    skip_count += 1
                    continue

            # 2. Doctors: avoid UQ_Doctors_Email and UQ_Doctors_RegNumber violations
            elif tbl == "Doctors":
                ms_cur.execute(
                    "SELECT doctor_id FROM [clinical].[Doctors] WHERE [doctor_id] = ? OR [email] = ? OR [registration_number] = ?",
                    (pk_val, row_dict.get("email"), row_dict.get("registration_number")),
                )
                existing_doc = ms_cur.fetchone()
                if existing_doc:
                    # Update fields from SQLite
                    ms_cur.execute(
                        """UPDATE [clinical].[Doctors]
                           SET [password_hash] = ?, [full_name] = ?, [medical_degree] = ?,
                               [email_verified] = ?, [verification_status] = ?, [is_active] = ?,
                               [username] = ?
                           WHERE [doctor_id] = ?""",
                        (
                            row_dict.get("password_hash"),
                            row_dict.get("full_name"),
                            row_dict.get("medical_degree"),
                            bool(row_dict.get("email_verified", 0)),
                            row_dict.get("verification_status", "PENDING"),
                            bool(row_dict.get("is_active", 1)),
                            row_dict.get("username"),
                            existing_doc[0],
                        ),
                    )
                    skip_count += 1
                    continue

            # 3. DoctorSessions: check session_id
            elif tbl == "DoctorSessions":
                ms_cur.execute(
                    "SELECT session_id FROM [clinical].[DoctorSessions] WHERE [session_id] = ?",
                    (pk_val,),
                )
                if ms_cur.fetchone():
                    skip_count += 1
                    continue

            # 4. Assessments: check id or assessment_code
            elif tbl == "Assessments":
                ms_cur.execute(
                    "SELECT id FROM [clinical].[Assessments] WHERE [id] = ? OR [assessment_code] = ?",
                    (pk_val, row_dict.get("assessment_code")),
                )
                if ms_cur.fetchone():
                    skip_count += 1
                    continue

            # 5. Predictions: check id or prediction_code
            elif tbl == "Predictions":
                ms_cur.execute(
                    "SELECT id FROM [clinical].[Predictions] WHERE [id] = ? OR [prediction_code] = ?",
                    (pk_val, row_dict.get("prediction_code")),
                )
                if ms_cur.fetchone():
                    skip_count += 1
                    continue

            # 6. EmailOTP: check otp_id
            elif tbl == "EmailOTP":
                ms_cur.execute(
                    "SELECT otp_id FROM [clinical].[EmailOTP] WHERE [otp_id] = ?",
                    (pk_val,),
                )
                if ms_cur.fetchone():
                    skip_count += 1
                    continue

            # General PK check fallback
            else:
                ms_cur.execute(f"SELECT 1 FROM [clinical].[{tbl}] WHERE [{pk_col}] = ?", (pk_val,))
                if ms_cur.fetchone():
                    skip_count += 1
                    continue

            # Prepare row values with boolean conversion for BIT columns
            vals = []
            for c in col_names:
                v = row_dict[c]
                if isinstance(v, int) and c in (
                    "is_active", "email_verified", "is_revoked", "is_used", "document_uploaded", "is_prediction_stale"
                ):
                    vals.append(bool(v))
                else:
                    vals.append(v)

            insert_sql = f"INSERT INTO [clinical].[{tbl}] ({cols_joined}) VALUES ({placeholders})"
            try:
                ms_cur.execute(insert_sql, tuple(vals))
                insert_count += 1
            except Exception as ins_err:
                print(f"[FATAL INSERT ERROR on {tbl} with PK={pk_val}]: {ins_err}")
                ms_conn.rollback()
                sq_conn.close()
                ms_conn.close()
                sys.exit(1)

        ms_conn.commit()

        # Query final row count in SQL Server
        ms_cur.execute(f"SELECT COUNT(*) FROM [clinical].[{tbl}]")
        ms_count = ms_cur.fetchone()[0]
        report[tbl] = {
            "sqlite": sq_count,
            "sql_server": ms_count,
            "inserted": insert_count,
            "updated_or_skipped": skip_count,
        }
        print(f"Table [clinical].[{tbl}]: SQLite={sq_count} | Inserted={insert_count} | Synced/Skipped={skip_count} | Total in SQL Server={ms_count}")

    # Verify foreign key referential integrity in SQL Server
    print("\nVerifying foreign-key relationships in SQL Server...")
    ms_cur.execute("""
        SELECT COUNT(*) FROM [clinical].[Assessments] a
        WHERE a.doctor_id IS NOT NULL 
          AND NOT EXISTS (SELECT 1 FROM [clinical].[Doctors] d WHERE d.doctor_id = a.doctor_id)
    """)
    orphan_assessments = ms_cur.fetchone()[0]
    assert orphan_assessments == 0, f"Integrity Failure: Found {orphan_assessments} orphan Assessments with invalid doctor_id!"

    ms_cur.execute("""
        SELECT COUNT(*) FROM [clinical].[DoctorSessions] s
        WHERE NOT EXISTS (SELECT 1 FROM [clinical].[Doctors] d WHERE d.doctor_id = s.doctor_id)
    """)
    orphan_sessions = ms_cur.fetchone()[0]
    assert orphan_sessions == 0, f"Integrity Failure: Found {orphan_sessions} orphan DoctorSessions with invalid doctor_id!"

    print("✓ All foreign-key relationships verified (0 orphan records).")

    sq_conn.close()
    ms_conn.close()

    print("\n==================================================")
    print("MIGRATION SUMMARY & ROW-COUNT AUDIT")
    print("==================================================")
    for t, stats in report.items():
        status_str = "MATCH" if stats["sqlite"] <= stats["sql_server"] else "MISMATCH"
        print(f" - {t:16s}: SQLite={stats['sqlite']:3d} | SQL Server={stats['sql_server']:3d} [{status_str}]")
    print("==================================================")


def main():
    print("==================================================")
    print("STARTING DATABASE MIGRATION: SQLITE -> SQL SERVER")
    print("==================================================")
    backup_sqlite()
    verify_connection()
    prepare_and_align_schema()
    migrate_data()
    print("\n✓ Database migration completed successfully.")


if __name__ == "__main__":
    main()
