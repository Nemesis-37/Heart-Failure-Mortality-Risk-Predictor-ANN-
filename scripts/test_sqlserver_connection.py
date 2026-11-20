import os
import sys
import urllib.parse
from pathlib import Path
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(PROJECT_ROOT / ".env")

# Check DB_CONNECTION_STRING from env or use the configured string
raw_conn_str = os.getenv(
    "DB_CONNECTION_STRING",
    "DRIVER={ODBC Driver 18 for SQL Server};SERVER=DESKTOP-NA0D6N1\\SQLEXPRESS;DATABASE=HeartMortalityPredictor;Trusted_Connection=yes;Encrypt=yes;TrustServerCertificate=yes;"
).strip("\"'")

print("--- SQL SERVER CONNECTION TEST ---")
print("Raw ODBC Connection String (without sensitive parts):")
safe_display = ";".join([p for p in raw_conn_str.split(";") if not p.lower().startswith("pwd")])
print(safe_display)

import pyodbc
from sqlalchemy import create_engine, text

# 1. Direct pyodbc test
print("\n[Step 1] Testing direct pyodbc connection...")
try:
    pyodbc_conn = pyodbc.connect(raw_conn_str, timeout=5)
    cursor = pyodbc_conn.cursor()
    cursor.execute("SELECT @@SERVERNAME, DB_NAME(), @@VERSION")
    server_name, db_name, version = cursor.fetchone()
    print("SUCCESS: pyodbc connected!")
    print(f" - Server Name: {server_name}")
    print(f" - Connected Database: {db_name}")
    print(f" - SQL Server Version: {version.splitlines()[0]}")
    pyodbc_conn.close()
except Exception as e:
    print(f"FAILED: pyodbc error: {type(e).__name__}: {e}")
    sys.exit(1)

# 2. SQLAlchemy mssql+pyodbc test
print("\n[Step 2] Testing SQLAlchemy mssql+pyodbc connection...")
try:
    sqlalchemy_url = f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(raw_conn_str)}"
    engine = create_engine(sqlalchemy_url, echo=False)
    with engine.connect() as conn:
        result = conn.execute(text("SELECT @@SERVERNAME AS srv, DB_NAME() AS db"))
        row = result.fetchone()
        print("SUCCESS: SQLAlchemy connected!")
        print(f" - Engine Dialect: {engine.dialect.name}")
        print(f" - Server: {row[0]}")
        print(f" - Database: {row[1]}")
        assert row[1].lower() == "heartmortalitypredictor".lower(), f"Expected HeartMortalityPredictor, got {row[1]}"
        print("✓ Database verified as HeartMortalityPredictor!")
    engine.dispose()
except Exception as e:
    print(f"FAILED: SQLAlchemy error: {type(e).__name__}: {e}")
    sys.exit(1)

print("\nALL CONNECTION TESTS PASSED!")
