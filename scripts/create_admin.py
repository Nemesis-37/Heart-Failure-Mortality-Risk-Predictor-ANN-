"""
scripts/create_admin.py
=======================
Controlled Administrator Account Setup Script.

Usage:
    .\\venv\\Scripts\\python.exe scripts\\create_admin.py
Or with arguments:
    .\\venv\\Scripts\\python.exe scripts\\create_admin.py --username admin --email admin@hospital.org --name "Chief Medical Officer" --password "AdminSecure2026!"
"""

import argparse
import getpass
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def create_admin():
    parser = argparse.ArgumentParser(description="Create a secure hospital administrator account")
    parser.add_argument("--username", help="Admin username")
    parser.add_argument("--email", help="Admin professional email")
    parser.add_argument("--name", help="Admin full name")
    parser.add_argument("--role", default="Medical Credentialing Officer", help="Administrative role")
    parser.add_argument("--password", help="Admin password (or enter interactively)")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  CardioPredict — Hospital Administrator Account Setup")
    print("=" * 60)

    try:
        from database.config import SessionLocal, engine
        from database.models import Administrator, Base
        from auth.security import hash_password
    except ImportError as exc:
        print(f"[FAIL] Missing dependencies: {exc}")
        print("Please ensure sqlalchemy, pyodbc, and argon2-cffi are installed.")
        return False

    # Ensure tables exist
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as exc:
        print(f"[NOTE] Database create_all: {exc}")

    username = args.username or input("\nEnter administrator username (e.g. admin): ").strip()
    if not username:
        print("[ERROR] Username cannot be empty.")
        return False

    email = args.email or input("Enter administrator email (e.g. admin@hospital.org): ").strip().lower()
    if "@" not in email:
        print("[ERROR] Invalid email address format.")
        return False

    full_name = args.name or input("Enter administrator full name (e.g. Dr. Eleanor Vance): ").strip()
    role = args.role or "Chief Medical Credentialing Officer"

    if args.password:
        password = args.password
    else:
        password = getpass.getpass("Enter administrator password: ")
        confirm_pwd = getpass.getpass("Confirm administrator password: ")
        if password != confirm_pwd:
            print("[ERROR] Passwords do not match.")
            return False

    if len(password) < 8:
        print("[ERROR] Password must be at least 8 characters long.")
        return False

    db = SessionLocal()
    try:
        # Check if username or email exists
        existing = (
            db.query(Administrator)
            .filter((Administrator.username == username) | (Administrator.email == email))
            .first()
        )
        if existing:
            print(f"\n[WARNING] Administrator with username '{username}' or email '{email}' already exists.")
            update = input("Do you wish to update this administrator's password? (y/N): ").strip().lower()
            if update == "y":
                existing.password_hash = hash_password(password)
                existing.full_name = full_name
                existing.role = role
                existing.is_active = True
                db.commit()
                print(f"[OK] Administrator '{username}' credentials updated successfully!")
                return True
            else:
                print("Operation cancelled.")
                return False

        # Create new Administrator
        new_admin = Administrator(
            admin_id=str(uuid.uuid4()),
            username=username,
            email=email,
            password_hash=hash_password(password),
            full_name=full_name,
            role=role,
            is_active=True,
            created_at=datetime.now(timezone.utc),
        )
        db.add(new_admin)
        db.commit()
        print(f"\n[SUCCESS] Administrator account '{username}' created successfully!")
        print(f"  - Admin ID   : {new_admin.admin_id}")
        print(f"  - Email      : {email}")
        print(f"  - Full Name  : {full_name}")
        print(f"  - Role       : {role}")
        print("\nYou can now sign in to the Administrator Verification Portal.")
        return True

    finally:
        db.close()


if __name__ == "__main__":
    success = create_admin()
    sys.exit(0 if success else 1)
