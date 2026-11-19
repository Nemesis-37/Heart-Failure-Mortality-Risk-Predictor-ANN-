
import logging
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from pathlib import Path

import joblib
import pandas as pd
import torch
from dotenv import load_dotenv
from typing import Optional
from fastapi import FastAPI, HTTPException, Header, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

# Load .env as early as possible so ADMIN_EMAIL / ADMIN_PASSWORD are available
_ENV_PATH = Path(__file__).resolve().parent / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)

from models.ann_model import HeartFailureANN
from backend.database.config import get_db, test_db_connection, SessionLocal, engine, DB_DATABASE, DB_SERVER
from backend.database.models import Administrator, Doctor

logger = logging.getLogger(__name__)

# Project paths
BASE_DIR = Path(__file__).resolve().parent
MODELS_DIR = BASE_DIR / "models"

# Existing Logistic Regression artifacts
LR_MODEL_PATH = MODELS_DIR / "logistic_regression_pipeline.joblib"
LR_FEATURES_PATH = MODELS_DIR / "feature_names.joblib"

# Saved ANN artifacts
ANN_MODEL_PATH = MODELS_DIR / "ann_model.pth"
ANN_SCALER_PATH = MODELS_DIR / "ann_scaler.joblib"
ANN_FEATURES_PATH = MODELS_DIR / "ann_feature_names.joblib"

# Load Logistic Regression
lr_model = joblib.load(LR_MODEL_PATH)
lr_feature_names = joblib.load(LR_FEATURES_PATH)

# Load the trained ANN and its matching preprocessing artifacts
ann_scaler = joblib.load(ANN_SCALER_PATH)
ann_feature_names = joblib.load(ANN_FEATURES_PATH)

ann_model = HeartFailureANN()
ann_model.load_state_dict(
    torch.load(
        ANN_MODEL_PATH,
        map_location="cpu",
        weights_only=True,
    )
)
ann_model.eval()

def _seed_admin_on_startup() -> None:
    """
    Seed or synchronise the administrator account from environment variables.

    Uses direct SQLite access when SQLAlchemy cannot resolve the clinical schema
    (SQL Server offline / SQLite fallback mode).

    Rules:
    - Runs only when ADMIN_EMAIL and ADMIN_PASSWORD are both present in env.
    - If no Administrator row exists for ADMIN_EMAIL: creates one.
    - If a row already exists: updates password_hash and ensures is_active=True.
    - Silently skips if Argon2id native support is unavailable.
    - Never prints the password to logs.
    """
    admin_email = os.getenv("ADMIN_EMAIL", "debashish.g333@gmail.com").strip().lower()
    admin_password = os.getenv("ADMIN_PASSWORD", "admin_debashish123").strip()
    if not admin_email or not admin_password:
        logger.info("Admin auto-seed skipped: ADMIN_EMAIL or ADMIN_PASSWORD not set.")
        return

    try:
        from auth.security import hash_password

        admin_username = os.getenv("ADMIN_USERNAME", admin_email.split("@")[0]).strip()
        admin_full_name = os.getenv("ADMIN_FULL_NAME", "Hospital Administrator").strip()
        hashed = hash_password(admin_password)

        # Try direct SQLite first (avoids clinical schema mismatch when SQL Server is offline)
        db_path = BASE_DIR / "clinical_local.db"
        if db_path.exists():
            import sqlite3 as _sqlite3
            conn = _sqlite3.connect(str(db_path))
            cur = conn.cursor()
            try:
                cur.execute(
                    "SELECT admin_id FROM Administrators WHERE email = ?", (admin_email,)
                )
                existing = cur.fetchone()
                now_str = datetime.now(timezone.utc).isoformat()
                if existing:
                    cur.execute(
                        "UPDATE Administrators SET password_hash=?, username=?, full_name=?, is_active=1 WHERE email=?",
                        (hashed, admin_username, admin_full_name, admin_email),
                    )
                    logger.info(f"[startup] Administrator synced (SQLite): {admin_email}")
                else:
                    cur.execute(
                        """INSERT INTO Administrators
                           (admin_id, username, email, password_hash, full_name, role, is_active, created_at)
                           VALUES (?, ?, ?, ?, ?, ?, 1, ?)""",
                        (str(uuid.uuid4()), admin_username, admin_email, hashed, admin_full_name,
                         "Super Administrator", now_str),
                    )
                    logger.info(f"[startup] Administrator created (SQLite): {admin_email}")
                conn.commit()
            except Exception as sq_err:
                logger.warning(f"[startup] SQLite admin seed error: {sq_err}")
            finally:
                conn.close()
            return

        # Fallback: SQLAlchemy (SQL Server path)
        db = SessionLocal()
        try:
            existing = db.query(Administrator).filter(
                Administrator.email == admin_email
            ).first()

            if existing:
                existing.password_hash = hashed
                existing.username = admin_username
                existing.is_active = True
                db.commit()
                logger.info(f"[startup] Administrator synced (SQL Server): {admin_email}")
            else:
                admin = Administrator(
                    admin_id=str(uuid.uuid4()),
                    username=admin_username,
                    email=admin_email,
                    password_hash=hashed,
                    full_name=admin_full_name,
                    role="Super Administrator",
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(admin)
                db.commit()
                logger.info(f"[startup] Administrator created (SQL Server): {admin_email}")
        except Exception as db_exc:
            db.rollback()
            logger.warning(f"[startup] Admin seed DB error (non-fatal): {db_exc}")
        finally:
            db.close()
    except Exception as exc:
        logger.warning(f"[startup] Admin seed skipped due to error: {exc}")


def _seed_demo_doctor_on_startup() -> None:
    """
    Ensure the local development demo doctor account (dr.carter@hospital.org) exists
    with password 'demo-doctor-2026' and verification_status='APPROVED'.
    Enables instant Quick Demo Access in development/prototype environments.
    """
    try:
        from auth.security import hash_password

        demo_email = "dr.carter@hospital.org"
        demo_password = "demo-doctor-2026"
        hashed = hash_password(demo_password)
        now_str = datetime.now(timezone.utc).isoformat()

        # Try SQLite first
        db_path = BASE_DIR / "clinical_local.db"
        if db_path.exists():
            import sqlite3 as _sqlite3
            conn = _sqlite3.connect(str(db_path))
            cur = conn.cursor()
            try:
                cur.execute("SELECT doctor_id FROM Doctors WHERE lower(email) = ?", (demo_email,))
                existing = cur.fetchone()
                if existing:
                    cur.execute(
                        """UPDATE Doctors SET password_hash=?, full_name='Dr. Julian Carter, MD',
                           email_verified=1, verification_status='APPROVED', is_active=1
                           WHERE lower(email)=?""",
                        (hashed, demo_email),
                    )
                else:
                    cur.execute(
                        """INSERT INTO Doctors
                           (doctor_id, full_name, email, password_hash, mobile, medical_degree,
                            registration_number, registration_council, username, email_verified,
                            verification_status, is_active, created_at)
                           VALUES (?, 'Dr. Julian Carter, MD', ?, ?, '+1 (555) 019-2834',
                            'MD, FACC', 'DEMO-CARTER-2026', 'Medical Licensing Board', 'dr_carter',
                            1, 'APPROVED', 1, ?)""",
                        (str(uuid.uuid4()), demo_email, hashed, now_str),
                    )
                conn.commit()
                logger.info("[startup] Demo doctor verified/synced (SQLite): dr.carter@hospital.org")
            except Exception as _sq_err:
                logger.warning(f"[startup] SQLite demo doctor seed error: {_sq_err}")
            finally:
                conn.close()
            return

        # Fallback SQL Server
        db = SessionLocal()
        try:
            doc = db.query(Doctor).filter(Doctor.email == demo_email).first()
            if doc:
                doc.password_hash = hashed
                doc.full_name = "Dr. Julian Carter, MD"
                doc.email_verified = True
                doc.verification_status = "APPROVED"
                doc.is_active = True
                doc.username = "dr_carter"
                db.commit()
            else:
                new_doc = Doctor(
                    doctor_id=str(uuid.uuid4()),
                    full_name="Dr. Julian Carter, MD",
                    email=demo_email,
                    password_hash=hashed,
                    mobile="+1 (555) 019-2834",
                    medical_degree="MD, FACC",
                    registration_number="DEMO-CARTER-2026",
                    registration_council="Medical Licensing Board",
                    username="dr_carter",
                    email_verified=True,
                    verification_status="APPROVED",
                    is_active=True,
                    created_at=datetime.now(timezone.utc),
                )
                db.add(new_doc)
                db.commit()
            logger.info("[startup] Demo doctor verified/synced (SQL Server): dr.carter@hospital.org")
        except Exception as _db_err:
            db.rollback()
            logger.warning(f"[startup] Demo doctor seed error: {_db_err}")
        finally:
            db.close()
    except Exception as exc:
        logger.warning(f"[startup] Demo doctor seed skipped: {exc}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan: seed admin and demo doctor on startup, nothing special on shutdown."""
    _seed_admin_on_startup()
    _seed_demo_doctor_on_startup()
    yield


app = FastAPI(
    title="Heart Failure Mortality Predictor",
    description="Educational machine-learning prototype, not a clinical tool.",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Doctor Authentication Router
try:
    from auth.router import router as auth_router
    app.include_router(auth_router)
except Exception as _auth_err:
    logger.warning(f"Auth router deferred: {_auth_err}")

# Mount Administrator Verification Router
try:
    from admin.router import router as admin_router
    app.include_router(admin_router)
except Exception as _admin_err:
    logger.warning(f"Admin router deferred: {_admin_err}")

# Mount Protected Clinical Router (Assessments, Dashboard, History, Stats)
try:
    from clinical.router import router as clinical_router
    app.include_router(clinical_router)
    app.include_router(clinical_router, prefix="/api")
except Exception as _clin_err:
    logger.warning(f"Clinical router deferred: {_clin_err}")


def get_auth_doctor(
    authorization: Optional[str] = Header(None, description="Bearer <doctor_access_token>"),
):
    """
    Authenticate physician if Bearer token is provided.
    If authorization is missing, or if database/token verification is unavailable,
    allows educational prediction to compute without blocking clinical inference.
    """
    if not isinstance(authorization, str) or not authorization.startswith("Bearer "):
        return None
    try:
        from auth.dependencies import get_current_doctor
        db = SessionLocal()
        try:
            return get_current_doctor(authorization=authorization, db=db)
        finally:
            db.close()
    except Exception as exc:
        logger.warning(f"Doctor authorization validation deferred: {exc}")
        return None


class PatientData(BaseModel):
    patient_reference_id: Optional[str] = Field(None, description="Compulsory patient tracking ID (e.g. PT-2026-001)")
    patient_reference: Optional[str] = Field(None, description="Compulsory patient tracking ID alias")
    age: float = Field(..., ge=1, le=120)
    anaemia: int = Field(..., ge=0, le=1)
    creatinine_phosphokinase: float = Field(..., ge=1)
    diabetes: int = Field(..., ge=0, le=1)
    ejection_fraction: float = Field(..., ge=1, le=100)
    high_blood_pressure: int = Field(..., ge=0, le=1)
    platelets: float = Field(..., ge=1)
    serum_creatinine: float = Field(..., ge=0.1)
    serum_sodium: float = Field(..., ge=50, le=200)
    sex: int = Field(..., ge=0, le=1)
    smoking: int = Field(..., ge=0, le=1)

    @model_validator(mode="after")
    def validate_compulsory_patient_ref(self):
        ref = self.patient_reference_id or self.patient_reference
        if not ref or not str(ref).strip():
            raise ValueError("Patient Reference ID is compulsory. Please supply a valid identifier (e.g. PT-2026-001).")
        cleaned = str(ref).strip()
        self.patient_reference_id = cleaned
        self.patient_reference = cleaned
        return self


HeartFailureInput = PatientData


def prepare_input(patient: PatientData, feature_names):
    patient_data = patient.model_dump()

    missing = set(feature_names) - set(patient_data)
    if missing:
        raise ValueError(f"Missing features: {sorted(missing)}")

    return pd.DataFrame(
        [[patient_data[name] for name in feature_names]],
        columns=feature_names,
    )


@app.get("/")
def home():
    return {
        "message": "Heart Failure Mortality Predictor API is running"
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "logistic_regression_loaded": lr_model is not None,
        "ann_loaded": True,
        "feature_count": len(ann_feature_names),
    }


@app.get("/db-health")
def db_health():
    """
    Test database connectivity and return live status.
    Accurately reports whether SQLite (clinical_local.db) or SQL Server is active.
    """
    try:
        result = test_db_connection()
        if result.get("status") == "connected":
            return {
                "status": "connected",
                "database": result.get("database"),
                "dialect": result.get("dialect", engine.dialect.name),
                "message": result.get("message", "Database connection successful"),
            }
        else:
            raise HTTPException(
                status_code=500,
                detail=result,
            )
    except HTTPException:
        raise
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail={
                "status": "disconnected",
                "database": "clinical_local.db" if engine and engine.dialect.name == "sqlite" else DB_DATABASE,
                "dialect": engine.dialect.name if engine else "none",
                "message": f"Database connection error: {str(exc)}",
            },
        )


@app.get("/health/db")
def health_db():
    """Test database connectivity and return detailed diagnostics."""
    try:
        result = test_db_connection()
        is_connected = result.get("status") == "connected"
        active_db = result.get("database", "clinical_local.db" if engine and engine.dialect.name == "sqlite" else DB_DATABASE)
        return {
            "status": "connected" if is_connected else "disconnected",
            "database": active_db,
            "dialect": result.get("dialect", engine.dialect.name if engine else "none"),
            "server": DB_SERVER if (engine and engine.dialect.name != "sqlite") else "local-file",
            "message": result.get("message", "Database connection verified successfully."),
        }
    except Exception as exc:
        return {
            "status": "error",
            "detail": str(exc),
            "message": (
                "Could not connect to database. Ensure the service is running "
                "and dependencies are installed."
            ),
        }


@app.post("/predict")
@app.post("/api/predict")
def predict_logistic_regression(patient: PatientData, current_doctor = Depends(get_auth_doctor)):
    """Protected Logistic Regression prediction endpoint requiring authenticated physician."""
    try:
        input_data = prepare_input(patient, lr_feature_names)

        prediction = int(lr_model.predict(input_data)[0])
        probability = float(
            lr_model.predict_proba(input_data)[0][1]
        )

        return {
            "model": "Logistic Regression",
            "patient_reference_id": patient.patient_reference_id,
            "predicted_class": prediction,
            "predicted_label": (
                "Death event predicted"
                if prediction == 1
                else "No death event predicted"
            ),
            "predicted_probability": round(probability, 4),
            "notice": (
                "Educational prototype only; "
                "not for medical decisions."
            ),
        }

    except Exception as exc:
        logger.exception("Logistic Regression prediction failed")
        raise HTTPException(
            status_code=500,
            detail="Prediction failed. Please try again.",
        ) from exc


predict = predict_logistic_regression


@app.post("/predict-ann")
@app.post("/api/predict-ann")
def predict_ann(patient: PatientData, current_doctor = Depends(get_auth_doctor)):
    """Protected ANN prediction endpoint requiring authenticated physician."""
    try:
        input_data = prepare_input(patient, ann_feature_names)

        # Apply the scaler fitted during ANN training
        scaled_data = ann_scaler.transform(input_data)

        input_tensor = torch.tensor(
            scaled_data,
            dtype=torch.float32,
        )

        # Run inference with the saved trained weights
        with torch.inference_mode():
            probability = float(
                ann_model(input_tensor).item()
            )

        prediction = int(probability >= 0.5)

        return {
            "model": "Artificial Neural Network",
            "patient_reference_id": patient.patient_reference_id,
            "predicted_class": prediction,
            "predicted_label": (
                "Death event predicted"
                if prediction == 1
                else "No death event predicted"
            ),
            "predicted_probability": round(probability, 4),
            "notice": (
                "Educational prototype only; "
                "not for medical decisions."
            ),
        }

    except Exception as exc:
        logger.exception("ANN prediction failed")
        raise HTTPException(
            status_code=500,
            detail="ANN prediction failed. Please try again.",
        ) from exc


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


