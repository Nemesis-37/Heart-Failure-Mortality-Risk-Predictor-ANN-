"""Create or update the configured administrator using local environment values."""

import os
import sys
import uuid
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import func

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from auth.security import hash_password, is_argon2_native
from database import SessionLocal
from database.models import Administrator


def main() -> int:
    email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    password = os.getenv("ADMIN_PASSWORD", "")
    configured_username = os.getenv("ADMIN_USERNAME", "").strip()

    if not email or "@" not in email or not password:
        print("Set valid ADMIN_EMAIL and ADMIN_PASSWORD environment variables.", file=sys.stderr)
        return 1
    if len(password) < 8:
        print("ADMIN_PASSWORD must contain at least 8 characters.", file=sys.stderr)
        return 1
    if not is_argon2_native():
        print("Native Argon2id support is required to provision the administrator.", file=sys.stderr)
        return 1

    db = SessionLocal()
    try:
        admin = db.query(Administrator).filter(func.lower(Administrator.email) == email).first()
        if admin is None:
            username = configured_username or email.split("@", 1)[0]
            username_conflict = db.query(Administrator).filter(
                func.lower(Administrator.username) == username.lower()
            ).first()
            if username_conflict:
                print("ADMIN_USERNAME is already assigned to another administrator.", file=sys.stderr)
                return 1
            admin = Administrator(
                admin_id=str(uuid.uuid4()),
                username=username,
                email=email,
                password_hash=hash_password(password),
                full_name="Hospital Administrator",
                role="Super Administrator",
                is_active=True,
            )
            db.add(admin)
        else:
            if configured_username and configured_username.lower() != admin.username.lower():
                username_conflict = db.query(Administrator).filter(
                    func.lower(Administrator.username) == configured_username.lower(),
                    Administrator.admin_id != admin.admin_id,
                ).first()
                if username_conflict:
                    print("ADMIN_USERNAME is already assigned to another administrator.", file=sys.stderr)
                    return 1
                admin.username = configured_username
            admin.email = email
            admin.password_hash = hash_password(password)
            admin.is_active = True

        db.commit()
        print("Administrator account provisioned successfully with an Argon2id password hash.")
        return 0
    except Exception as exc:
        db.rollback()
        print(f"Administrator provisioning failed: {exc}", file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
