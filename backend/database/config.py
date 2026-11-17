"""
backend/database/config.py
==========================
Single Central Source of Truth for SQLAlchemy Database Configuration in the
Heart Failure Mortality Risk Predictor application.

Features:
- Primary Engine: Microsoft SQL Server via ODBC Driver 18 (configurable via environment variables)
- Development / Active Fallback Engine: SQLite (clinical_local.db) with WAL journal mode and busy_timeout
- Thread-safe SessionLocal session factory
- Declarative Base for all ORM models
- get_db session dependency with automatic rollback on failure and session closing
- test_db_connection() and test_connection() utilities for diagnostics and health endpoints
"""

import logging
import os
import urllib.parse
from pathlib import Path
from typing import Generator

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.dialects.mssql import DATETIMEOFFSET, UNIQUEIDENTIFIER
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

# Register SQLite dialect mappings for MSSQL specific types if SQLite is active
@compiles(DATETIMEOFFSET, "sqlite")
def _compile_datetimeoffset_sqlite(type_, compiler, **kw):
    return "DATETIME"

@compiles(UNIQUEIDENTIFIER, "sqlite")
def _compile_uniqueidentifier_sqlite(type_, compiler, **kw):
    return "VARCHAR(64)"

# ---------------------------------------------------------------------------
# Load .env from project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = PROJECT_ROOT / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()

# ---------------------------------------------------------------------------
# Read connection settings from environment variables
# ---------------------------------------------------------------------------
def _get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()

DB_SERVER = _get_env("SERVER", _get_env("DB_SERVER", r".\SQLEXPRESS"))
DB_DATABASE = _get_env("DATABASE", _get_env("DB_NAME", _get_env("DB_DATABASE", "HeartMortalityPredictor")))
DB_AUTH_MODE = _get_env("DB_AUTH_MODE", "windows").lower()
DB_USERNAME = _get_env("DB_USERNAME")
DB_PASSWORD = _get_env("DB_PASSWORD")
DB_DRIVER = _get_env("DRIVER", _get_env("DB_DRIVER", "{ODBC Driver 18 for SQL Server}"))
DB_TRUST_CONNECTION = _get_env("Trusted_Connection", _get_env("DB_TRUSTED_CONNECTION", "yes"))
DB_ENCRYPT = _get_env("Encrypt", _get_env("DB_ENCRYPT", "yes"))
DB_TRUST_SERVER_CERTIFICATE = _get_env("TrustServerCertificate", _get_env("DB_TRUST_SERVER_CERTIFICATE", "yes"))

DB_POOL_SIZE = int(_get_env("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(_get_env("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(_get_env("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(_get_env("DB_POOL_RECYCLE", "1800"))

# ---------------------------------------------------------------------------
# Build the ODBC connection string
# ---------------------------------------------------------------------------
def _build_connection_string() -> str:
    clean_driver = DB_DRIVER.strip("{}")
    formatted_driver = f"{{{clean_driver}}}"

    params = {
        "DRIVER": formatted_driver,
        "SERVER": DB_SERVER,
        "DATABASE": DB_DATABASE,
        "Trusted_Connection": DB_TRUST_CONNECTION,
        "Encrypt": DB_ENCRYPT,
        "TrustServerCertificate": DB_TRUST_SERVER_CERTIFICATE,
        "Connection Timeout": "1",
    }

    if DB_AUTH_MODE == "sql" and DB_USERNAME and DB_PASSWORD:
        params["Trusted_Connection"] = "no"
        params["UID"] = DB_USERNAME
        params["PWD"] = DB_PASSWORD

    odbc_str = ";".join(f"{k}={v}" for k, v in params.items())
    return f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(odbc_str)}"

# ---------------------------------------------------------------------------
# SQLAlchemy Engine Initialization
# ---------------------------------------------------------------------------
try:
    import pyodbc  # noqa: F401
    HAS_PYODBC = True
except ImportError:
    HAS_PYODBC = False

engine = None
DATABASE_URL = None

if HAS_PYODBC:
    try:
        DATABASE_URL = _build_connection_string()
        _probe_engine = create_engine(DATABASE_URL, connect_args={"timeout": 2})
        with _probe_engine.connect() as _probe_conn:
            _probe_conn.execute(text("SELECT 1"))
        _probe_engine.dispose()

        engine = create_engine(
            DATABASE_URL,
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_MAX_OVERFLOW,
            pool_timeout=DB_POOL_TIMEOUT,
            pool_recycle=DB_POOL_RECYCLE,
            pool_pre_ping=True,
            echo=False,
            fast_executemany=True,
        )
    except Exception as exc:
        logger.info(f"SQL Server not reachable ({exc}). Falling back to local SQLite.")
        engine = None

if engine is None:
    # Active development fallback to SQLite
    sqlite_db_path = PROJECT_ROOT / "clinical_local.db"
    DATABASE_URL = f"sqlite:///{sqlite_db_path.as_posix()}"
    engine = create_engine(
        DATABASE_URL,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    @event.listens_for(engine, "connect")
    def _sqlite_connect_pragmas(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA busy_timeout=5000")
        cursor.close()

if engine is not None and engine.dialect.name == "sqlite":
    engine = engine.execution_options(schema_translate_map={"clinical": None})

# ---------------------------------------------------------------------------
# Session Factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)

# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Declarative Base class for all SQLAlchemy ORM models."""
    pass

# ---------------------------------------------------------------------------
# FastAPI Session Dependency
# ---------------------------------------------------------------------------
def get_db() -> Generator:
    """
    FastAPI dependency yielding a SQLAlchemy database session per request.
    Automatically handles session closing and rollback on transaction errors.
    """
    if engine is None:
        raise RuntimeError("Database engine is not initialized.")

    db = SessionLocal()
    try:
        yield db
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

# ---------------------------------------------------------------------------
# Diagnostic Connection Test Utilities
# ---------------------------------------------------------------------------
def test_connection() -> bool:
    """Fast boolean health check executing SELECT 1."""
    if engine is None:
        return False
    try:
        with engine.connect() as conn:
            res = conn.execute(text("SELECT 1")).scalar()
            return res == 1
    except Exception:
        return False

def test_db_connection() -> dict:
    """
    Detailed database health report verifying active engine and target database.
    Accurately identifies whether SQLite or SQL Server is currently serving traffic.
    """
    if engine is None:
        return {
            "status": "error",
            "database": DB_DATABASE,
            "dialect": "none",
            "message": "SQLAlchemy engine is not initialized.",
        }

    try:
        with engine.connect() as conn:
            if conn.dialect.name == "sqlite":
                conn.execute(text("SELECT 1"))
                return {
                    "status": "connected",
                    "database": "clinical_local.db",
                    "dialect": "sqlite",
                    "message": "Active SQLite fallback database connection verified (clinical_local.db)",
                }
            else:
                db_name = conn.execute(text("SELECT DB_NAME()")).scalar()
                return {
                    "status": "connected",
                    "database": db_name or DB_DATABASE,
                    "dialect": "mssql",
                    "message": "Microsoft SQL Server Express connection verified",
                }
    except Exception as exc:
        return {
            "status": "disconnected",
            "database": DB_DATABASE,
            "dialect": engine.dialect.name,
            "message": f"Database connection failed: {str(exc)}",
        }
