"""
seed_admin.py
=============
One-time administrator account setup script.

Usage:
    python seed_admin.py

You will be prompted for the administrator password.
Alternatively, set ADMIN_PASSWORD in your .env file and run:
    python seed_admin.py --from-env

This script reads ADMIN_EMAIL from .env and creates or updates
the Administrator record in the SQLite database (clinical_local.db).
"""

import argparse
import getpass
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

# ---------------------------------------------------------------------------
# Load .env
# ---------------------------------------------------------------------------
_ENV_PATH = Path(__file__).resolve().parent / ".env"
if _ENV_PATH.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_ENV_PATH)

# ---------------------------------------------------------------------------
# Silence SQLAlchemy SQL Server timeout noise during import
# ---------------------------------------------------------------------------
import logging
logging.basicConfig(level=logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

# ---------------------------------------------------------------------------
# Collect credentials
# ---------------------------------------------------------------------------
def collect_credentials(from_env: bool):
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    username = os.getenv("ADMIN_USERNAME", "").strip()
    full_name = os.getenv("ADMIN_FULL_NAME", "Hospital Administrator").strip()

    if not email:
        email = input("Administrator Email: ").strip().lower()
    if not username:
        username = email.split("@")[0]

    if from_env:
        password = os.getenv("ADMIN_PASSWORD", "").strip()
        if not password:
            print("ERROR: ADMIN_PASSWORD is not set in .env. Add it and retry.", file=sys.stderr)
            sys.exit(1)
    else:
        password = getpass.getpass(f"Password for {email}: ")
        confirm = getpass.getpass("Confirm password: ")
        if password != confirm:
            print("ERROR: Passwords do not match.", file=sys.stderr)
            sys.exit(1)

    if len(password) < 8:
        print("ERROR: Password must be at least 8 characters.", file=sys.stderr)
        sys.exit(1)

    return email, username, full_name, password


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    parser = argparse.ArgumentParser(description="Seed or update the administrator account.")
    parser.add_argument("--from-env", action="store_true", help="Read password from ADMIN_PASSWORD in .env")
    args = parser.parse_args()

    email, username, full_name, password = collect_credentials(args.from_env)

    # Import after env load so database picks up settings
    try:
        from auth.security import hash_password, is_argon2_native
    except ImportError as e:
        print(f"ERROR: Cannot import auth.security: {e}", file=sys.stderr)
        sys.exit(1)

    if not is_argon2_native():
        print("ERROR: Native Argon2id support is required. Install 'argon2-cffi'.", file=sys.stderr)
        sys.exit(1)

    # Get database session
    try:
        from database import SessionLocal
    except ImportError:
        from database.config import SessionLocal

    try:
        from database.models import Administrator
    except ImportError:
        print("ERROR: Cannot import Administrator model.", file=sys.stderr)
        sys.exit(1)

    db = SessionLocal()
    try:
        # Look for existing admin by email
        existing = db.query(Administrator).filter(
            Administrator.email == email
        ).first()

        hashed = hash_password(password)
        now = datetime.now(timezone.utc)

        if existing:
            existing.password_hash = hashed
            existing.username = username
            existing.full_name = full_name
            existing.is_active = True
            db.commit()
            print(f"[OK] Administrator account updated: {email}")
        else:
            admin = Administrator(
                admin_id=str(uuid.uuid4()),
                username=username,
                email=email,
                password_hash=hashed,
                full_name=full_name,
                role="Super Administrator",
                is_active=True,
                created_at=now,
            )
            db.add(admin)
            db.commit()
            print(f"[OK] Administrator account created: {email}")

        print(f"     Username : {username}")
        print(f"     Full name: {full_name}")
        print()
        print("You can now sign in through the unified login form.")
    except Exception as e:
        db.rollback()
        print(f"ERROR: Database operation failed: {e}", file=sys.stderr)
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
