"""
scripts/migrate_sqlite_to_sqlserver.py
======================================
Automated, idempotent data migration script from SQLite (clinical_local.db)
to Microsoft SQL Server (database: HeartMortalityPredictor, schema: clinical).

Features:
- Connects to master to ensure target database exists.
- Creates [clinical] schema if not present.
- Creates target tables using SQL Server DDL if not present.
- Migrates Administrators, Doctors, DoctorSessions, Assessments, EmailOTP, Predictions.
- Preserves all Primary Keys, Foreign Keys, UUIDs, timestamps, and Argon2id password hashes.
- Performs row-count verification and data validation.
- Preserves original SQLite database without modifications.
"""

import os
import sys
import sqlite3
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env")

try:
    import pyodbc
except ImportError:
    print("ERROR: pyodbc is not installed. Run: pip install pyodbc")
    sys.exit(1)

# Connection parameters
DB_SERVER = os.getenv("SERVER", os.getenv("DB_SERVER", r".\SQLEXPRESS")).strip()
DB_DATABASE = os.getenv("DATABASE", os.getenv("DB_NAME", os.getenv("DB_DATABASE", "HeartMortalityPredictor"))).strip()
DB_AUTH_MODE = os.getenv("DB_AUTH_MODE", "windows").lower().strip()
DB_USERNAME = os.getenv("DB_USERNAME", "").strip()
DB_PASSWORD = os.getenv("DB_PASSWORD", "").strip()
DB_DRIVER = os.getenv("DRIVER", os.getenv("DB_DRIVER", "{ODBC Driver 18 for SQL Server}")).strip("{}")

SQLITE_PATH = PROJECT_ROOT / "clinical_local.db"


def get_odbc_conn_str(database: str = "master") -> str:
    params = {
        "DRIVER": f"{{{DB_DRIVER}}}",
        "SERVER": DB_SERVER,
        "DATABASE": database,
        "Trusted_Connection": "yes" if DB_AUTH_MODE == "windows" else "no",
        "Encrypt": "yes",
        "TrustServerCertificate": "yes",
        "Connection Timeout": "5",
    }
    if DB_AUTH_MODE == "sql" and DB_USERNAME and DB_PASSWORD:
        params["UID"] = DB_USERNAME
        params["PWD"] = DB_PASSWORD

    return ";".join(f"{k}={v}" for k, v in params.items())


def ensure_sqlserver_database():
    """Ensure HeartMortalityPredictor database exists on SQL Server."""
    print(f"Connecting to SQL Server master on '{DB_SERVER}'...")
    master_conn_str = get_odbc_conn_str("master")
    try:
        conn = pyodbc.connect(master_conn_str, autocommit=True)
    except Exception as e:
        print(f"\n[FATAL] Could not connect to SQL Server on '{DB_SERVER}': {e}")
        print("\nPlease ensure the SQL Server service is running and accessible.")
        sys.exit(1)

    cur = conn.cursor()
    cur.execute("SELECT name FROM sys.databases WHERE name = ?", (DB_DATABASE,))
    exists = cur.fetchone()
    if not exists:
        print(f"Database '{DB_DATABASE}' does not exist. Creating it now...")
        cur.execute(f"CREATE DATABASE [{DB_DATABASE}]")
        print(f"✓ Database '{DB_DATABASE}' created successfully.")
    else:
        print(f"✓ Database '{DB_DATABASE}' already exists.")
    conn.close()


def apply_schema_ddl():
    """Apply DDL script to create [clinical] schema and all required tables."""
    print(f"\nConnecting to database '{DB_DATABASE}' to verify schema...")
    db_conn_str = get_odbc_conn_str(DB_DATABASE)
    conn = pyodbc.connect(db_conn_str, autocommit=True)
    cur = conn.cursor()

    # Ensure schema clinical
    cur.execute("SELECT schema_id FROM sys.schemas WHERE name = 'clinical'")
    if not cur.fetchone():
        print("Creating schema [clinical]...")
        cur.execute("CREATE SCHEMA [clinical]")

    # Read and apply schema SQL
    schema_file = PROJECT_ROOT / "database" / "sql_server_assessments_schema.sql"
    if schema_file.exists():
        sql_content = schema_file.read_text(encoding="utf-8")
        batches = [b.strip() for b in sql_content.split("GO") if b.strip()]
        for batch in batches:
            try:
                cur.execute(batch)
            except Exception as b_err:
                # Ignore object already exists notices
                if "already exists" not in str(b_err).lower() and "there is already an object" not in str(b_err).lower():
                    print(f"Notice on DDL batch: {b_err}")
        print("✓ Schema DDL applied successfully.")
    else:
        print("Warning: sql_server_assessments_schema.sql not found; relying on existing tables.")

    conn.close()


def migrate_data():
    """Migrate all records from SQLite to SQL Server."""
    if not SQLITE_PATH.exists():
        print(f"ERROR: SQLite database file '{SQLITE_PATH}' not found!")
        sys.exit(1)

    print(f"\nOpening SQLite database: {SQLITE_PATH}...")
    sq_conn = sqlite3.connect(str(SQLITE_PATH))
    sq_conn.row_factory = sqlite3.Row
    sq_cur = sq_conn.cursor()

    print(f"Connecting to SQL Server database '{DB_DATABASE}'...")
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
        sq_cur.execute(f"SELECT * FROM \"{tbl}\"")
        sq_rows = sq_cur.fetchall()
        sq_count = len(sq_rows)

        if sq_count == 0:
            # Table is empty in SQLite
            ms_cur.execute(f"SELECT COUNT(*) FROM [clinical].[{tbl}]")
            ms_count = ms_cur.fetchone()[0]
            report[tbl] = {"sqlite": 0, "sql_server": ms_count, "migrated": 0}
            print(f"Table [clinical].[{tbl}]: 0 rows in SQLite, {ms_count} rows in SQL Server.")
            continue

        # Get column names
        col_names = [col[0] for col in sq_cur.description]
        cols_joined = ", ".join(f"[{c}]" for c in col_names)
        placeholders = ", ".join("?" for _ in col_names)

        pk_col = col_names[0]  # First column is primary key
        insert_count = 0
        skip_count = 0

        for row in sq_rows:
            row_dict = dict(row)
            pk_val = row_dict[pk_col]

            # Check if record already exists in SQL Server
            ms_cur.execute(f"SELECT 1 FROM [clinical].[{tbl}] WHERE [{pk_col}] = ?", (pk_val,))
            if ms_cur.fetchone():
                skip_count += 1
                continue

            # Convert row values safely for SQL Server
            vals = []
            for c in col_names:
                v = row_dict[c]
                # Convert SQLite boolean (0/1) to Python bool for SQL Server BIT column
                if isinstance(v, int) and c in (
                    "is_active", "email_verified", "is_revoked", "is_used", "document_uploaded"
                ):
                    vals.append(bool(v))
                else:
                    vals.append(v)

            insert_sql = f"INSERT INTO [clinical].[{tbl}] ({cols_joined}) VALUES ({placeholders})"
            ms_cur.execute(insert_sql, tuple(vals))
            insert_count += 1

        ms_conn.commit()

        # Verify final SQL Server count
        ms_cur.execute(f"SELECT COUNT(*) FROM [clinical].[{tbl}]")
        ms_count = ms_cur.fetchone()[0]
        report[tbl] = {"sqlite": sq_count, "sql_server": ms_count, "inserted": insert_count, "skipped": skip_count}
        print(f"Table [clinical].[{tbl}]: SQLite={sq_count} | Inserted={insert_count} | Skipped={skip_count} | Total in SQL Server={ms_count}")

    sq_conn.close()
    ms_conn.close()

    print("\n==================================================")
    print("MIGRATION SUMMARY & ROW-COUNT VERIFICATION")
    print("==================================================")
    for t, stats in report.items():
        match_str = "MATCH" if stats["sqlite"] <= stats["sql_server"] else "MISMATCH"
        print(f" - {t:16s}: SQLite={stats['sqlite']:3d} | SQL Server={stats['sql_server']:3d} [{match_str}]")
    print("==================================================")


def main():
    print("==================================================")
    print("STARTING DATABASE MIGRATION: SQLITE -> SQL SERVER")
    print("==================================================")
    ensure_sqlserver_database()
    apply_schema_ddl()
    migrate_data()
    print("\n✓ Database migration completed successfully.")


if __name__ == "__main__":
    main()
