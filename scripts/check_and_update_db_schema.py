"""
scripts/check_and_update_db_schema.py
=====================================
Safely check and add username, last_login, and approved_at columns
to the Doctors table in SQLite databases (clinical_local.db and clinical_schema.db).
"""

import sqlite3
from pathlib import Path

DB_FILES = ["clinical_local.db", "clinical_schema.db"]

COLUMNS_TO_ADD = [
    ("username", "VARCHAR(64) UNIQUE"),
    ("last_login", "DATETIME"),
    ("approved_at", "DATETIME"),
]

def main():
    root = Path(__file__).resolve().parent.parent
    for db_name in DB_FILES:
        db_path = root / db_name
        if not db_path.exists():
            print(f"Skipping {db_name} (does not exist)")
            continue

        print(f"\nChecking {db_name}...")
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()

        # Check existing columns
        cur.execute("PRAGMA table_info(Doctors)")
        existing_cols = {row[1] for row in cur.fetchall()}
        print(f"Existing columns in Doctors: {sorted(list(existing_cols))}")

        for col_name, col_type in COLUMNS_TO_ADD:
            if col_name not in existing_cols:
                print(f"  Adding column {col_name} ({col_type})...")
                # SQLite ALTER TABLE does not support UNIQUE directly in ADD COLUMN in older syntax,
                # so add as VARCHAR(64) and create UNIQUE INDEX
                base_type = "VARCHAR(64)" if "VARCHAR" in col_type else "DATETIME"
                cur.execute(f"ALTER TABLE Doctors ADD COLUMN {col_name} {base_type}")
                if "UNIQUE" in col_type:
                    cur.execute(f"CREATE UNIQUE INDEX IF NOT EXISTS UQ_Doctors_{col_name} ON Doctors({col_name})")
                print(f"  Column {col_name} added successfully.")
            else:
                print(f"  Column {col_name} already exists.")

        conn.commit()
        conn.close()

if __name__ == "__main__":
    main()
