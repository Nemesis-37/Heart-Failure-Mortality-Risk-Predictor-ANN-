"""Create the local development demo doctor account when it does not exist.

Run with APP_ENV=development and DEMO_DOCTOR_PASSWORD set in the environment.
This script refuses to run against non-local SQL Server instances.
"""

import os
import socket
import sys
from pathlib import Path

from sqlalchemy import func, text

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from auth.security import hash_password, is_argon2_native, verify_password
from database import SessionLocal, engine
from database.models import Doctor


DEMO_EMAIL = "dr.carter@hospital.org"
DEMO_REGISTRATION_NUMBER = "DEMO-CARTER-LOCAL-2026"


def _require_local_development_database() -> str:
    if os.getenv("APP_ENV", "").strip().lower() != "development":
        raise RuntimeError("Set APP_ENV=development to create the demo account.")
    if engine.dialect.name != "mssql":
        raise RuntimeError("Demo account creation requires the configured local SQL Server.")

    with engine.connect() as connection:
        database_name, server_name = connection.execute(
            text("SELECT DB_NAME(), @@SERVERNAME")
        ).one()

    server_host = server_name.split("\\", 1)[0].casefold()
    local_hosts = {socket.gethostname().casefold(), "localhost", ".", "(local)"}
    if server_host not in local_hosts:
        raise RuntimeError("Refusing to create demo credentials on a non-local SQL Server.")

    return database_name


def create_demo_doctor() -> bool:
    database_name = _require_local_development_database()
    password = os.getenv("DEMO_DOCTOR_PASSWORD")
    if not password:
        raise RuntimeError("Set DEMO_DOCTOR_PASSWORD before creating the demo account.")
    if not is_argon2_native():
        raise RuntimeError("argon2-cffi is required to create an Argon2id demo password hash.")

    db = SessionLocal()
    try:
        matches = (
            db.query(Doctor)
            .filter(func.lower(Doctor.email) == DEMO_EMAIL)
            .all()
        )
        if matches:
            if len(matches) > 1:
                raise RuntimeError("Multiple matching demo doctor records exist; refusing to continue.")
            print(f"Demo doctor already exists in {database_name}; no changes made.")
            return True

        if db.query(Doctor).filter(
            Doctor.registration_number == DEMO_REGISTRATION_NUMBER
        ).first():
            raise RuntimeError("Demo registration number is already assigned to another doctor.")

        password_hash = hash_password(password)
        if not password_hash.startswith("$argon2id$") or not verify_password(
            password, password_hash
        ):
            raise RuntimeError("Generated demo password hash failed Argon2id verification.")

        doctor = Doctor(
            full_name="Dr. Carter (Demo)",
            email=DEMO_EMAIL,
            password_hash=password_hash,
            mobile="0000000000",
            medical_degree="MD",
            registration_number=DEMO_REGISTRATION_NUMBER,
            registration_council="Development Demo Only",
            email_verified=True,
            verification_status="APPROVED",
            is_active=True,
        )
        db.add(doctor)
        db.commit()
        print(f"Created the development demo doctor in {database_name}.")
        return True
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_demo_doctor()
