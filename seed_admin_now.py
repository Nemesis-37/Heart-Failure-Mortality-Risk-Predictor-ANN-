"""
seed_admin_now.py
=================
Seeds the administrator account with the password from ADMIN_PASSWORD env var.
Run once to initialize the administrator. After running, the account is ready.
"""
import logging
import os
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path

logging.basicConfig(level=logging.WARNING)
logging.getLogger("sqlalchemy").setLevel(logging.ERROR)

_ENV_PATH = Path(__file__).resolve().parent / ".env"
if _ENV_PATH.exists():
    from dotenv import load_dotenv
    load_dotenv(dotenv_path=_ENV_PATH)

admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
admin_password = os.getenv("ADMIN_PASSWORD", "").strip()
admin_username = os.getenv("ADMIN_USERNAME", "").strip()
admin_full_name = os.getenv("ADMIN_FULL_NAME", "Hospital Administrator").strip()

if not admin_email:
    print("ERROR: ADMIN_EMAIL not found in .env", file=sys.stderr)
    sys.exit(1)

if not admin_password:
    print("ERROR: ADMIN_PASSWORD not found in .env", file=sys.stderr)
    print("Please add ADMIN_PASSWORD=<your_password> to your .env file and retry.")
    sys.exit(1)

if not admin_username:
    admin_username = admin_email.split("@")[0]

try:
    from auth.security import hash_password, is_argon2_native
    assert is_argon2_native(), "Native Argon2id required"
except Exception as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

try:
    from database import SessionLocal
except ImportError:
    from database.config import SessionLocal

try:
    from database.models import Administrator
except ImportError as e:
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)

db = SessionLocal()
try:
    existing = db.query(Administrator).filter(Administrator.email == admin_email).first()
    hashed = hash_password(admin_password)
    now = datetime.now(timezone.utc)

    if existing:
        existing.password_hash = hashed
        existing.username = admin_username
        existing.full_name = admin_full_name
        existing.is_active = True
        db.commit()
        print(f"[OK] Administrator account updated  : {admin_email}")
    else:
        admin = Administrator(
            admin_id=str(uuid.uuid4()),
            username=admin_username,
            email=admin_email,
            password_hash=hashed,
            full_name=admin_full_name,
            role="Super Administrator",
            is_active=True,
            created_at=now,
        )
        db.add(admin)
        db.commit()
        print(f"[OK] Administrator account created  : {admin_email}")

    print(f"     Username   : {admin_username}")
    print(f"     Full name  : {admin_full_name}")
    print()
    print("Sign in through the unified login form at http://localhost:5173")
except Exception as e:
    db.rollback()
    print(f"ERROR: {e}", file=sys.stderr)
    sys.exit(1)
finally:
    db.close()
