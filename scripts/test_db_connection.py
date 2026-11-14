"""
scripts/test_db_connection.py
==============================
Standalone script to verify that the SQL Server connection works.

Run from the project root directory:

    .\\venv\\Scripts\\python.exe scripts\\test_db_connection.py

What this script checks
-----------------------
1. Loads .env configuration.
2. Builds the SQLAlchemy connection URL from environment variables.
3. Opens a physical connection to SQL Server.
4. Runs a minimal SELECT 1 query.
5. Checks that the target database exists.
6. Lists all tables in the 'clinical' schema (if any).
7. Confirms the SQLAlchemy session factory works.

If all checks pass, the database layer is ready for the next step.
"""

import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Make sure the project root is on the Python path so we can import
# database.config regardless of where this script is called from.
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _section(title: str) -> None:
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}")


def _ok(message: str) -> None:
    print(f"  [OK]  {message}")


def _fail(message: str) -> None:
    print(f"  [FAIL] {message}")


def run_checks() -> bool:
    """Run all connection checks. Returns True if all pass."""

    all_passed = True

    # ------------------------------------------------------------------
    # Step 1 — Import the database config module
    # ------------------------------------------------------------------
    _section("Step 1 — Import database configuration")
    try:
        from database.config import SessionLocal, engine, test_connection

        _ok("database.config imported successfully")
        _ok(f"Engine dialect : {engine.dialect.name}")
        _ok(f"Engine driver  : {engine.dialect.driver}")
    except ImportError as exc:
        _fail(f"Could not import database.config: {exc}")
        _fail("Make sure you have installed: sqlalchemy, pyodbc, python-dotenv")
        return False

    # ------------------------------------------------------------------
    # Step 2 — Test raw engine connection with SELECT 1
    # ------------------------------------------------------------------
    _section("Step 2 — Test engine connection (SELECT 1)")
    try:
        from sqlalchemy import text

        result = test_connection()
        if result:
            _ok("SELECT 1 returned 1 — connection is alive!")
        else:
            _fail("SELECT 1 did not return the expected value.")
            all_passed = False
    except Exception as exc:
        _fail(f"Connection failed: {exc}")
        _fail("")
        _fail("Common causes:")
        _fail("  - SQL Server Express service is not running")
        _fail("  - Instance name is wrong (check DB_INSTANCE in .env)")
        _fail("  - ODBC driver name is wrong (check DB_DRIVER in .env)")
        _fail("  - Database does not exist yet (create it in SSMS first)")
        _fail("  - Windows Authentication issue (check your user permissions)")
        all_passed = False

    if not all_passed:
        return False

    # ------------------------------------------------------------------
    # Step 3 — Check that the target database exists and is accessible
    # ------------------------------------------------------------------
    _section("Step 3 — Check database accessibility")
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            # This query returns the current database name
            db_name = conn.execute(text("SELECT DB_NAME()")).scalar()
            _ok(f"Connected to database: {db_name!r}")

            # Check SQL Server version
            version = conn.execute(text("SELECT @@VERSION")).scalar()
            version_line = version.split("\n")[0].strip()
            _ok(f"SQL Server version: {version_line}")

    except Exception as exc:
        _fail(f"Database check failed: {exc}")
        all_passed = False

    # ------------------------------------------------------------------
    # Step 4 — List tables in the 'clinical' schema
    # ------------------------------------------------------------------
    _section("Step 4 — Check 'clinical' schema tables")
    try:
        from sqlalchemy import text

        with engine.connect() as conn:
            rows = conn.execute(text("""
                SELECT TABLE_NAME
                FROM INFORMATION_SCHEMA.TABLES
                WHERE TABLE_SCHEMA = 'clinical'
                ORDER BY TABLE_NAME
            """)).fetchall()

        if rows:
            _ok(f"Found {len(rows)} table(s) in schema 'clinical':")
            for row in rows:
                print(f"       - clinical.{row[0]}")
        else:
            print("  [NOTE] No tables found in 'clinical' schema yet.")
            print("         Run the SQL schema script in SSMS to create them:")
            print("         database/sql_server_assessments_schema.sql")

    except Exception as exc:
        _fail(f"Schema check failed: {exc}")
        all_passed = False

    # ------------------------------------------------------------------
    # Step 5 — Test session factory
    # ------------------------------------------------------------------
    _section("Step 5 — Test SQLAlchemy session factory")
    try:
        from sqlalchemy import text

        db = SessionLocal()
        try:
            result = db.execute(text("SELECT GETDATE() AS now")).scalar()
            _ok(f"Session factory works — SQL Server time: {result}")
        finally:
            db.close()
            _ok("Session closed cleanly")

    except Exception as exc:
        _fail(f"Session factory failed: {exc}")
        all_passed = False

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    _section("Summary")
    if all_passed:
        print("  All checks passed! The database connection is ready.")
        print("  You can now proceed to Step 2 (doctor authentication).")
    else:
        print("  One or more checks failed. See messages above.")
        print("  Fix the issues and run this script again.")

    return all_passed


if __name__ == "__main__":
    success = run_checks()
    sys.exit(0 if success else 1)
