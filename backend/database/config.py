"""
backend/database/config.py
==========================
Single Central Source of Truth for SQLAlchemy Database Configuration in the
Heart Failure Mortality Risk Predictor application.

Features:
- Primary Engine: PostgreSQL (Local & Render Production) via psycopg2
- Dialect: postgresql+psycopg2
- Schema: [clinical] automatically created and set in search_path
- Offline Development Fallback: SQLite (clinical_local.db) with WAL mode
- Thread-safe SessionLocal session factory
- Shared Declarative Base for all ORM models
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
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Declarative Base (Single Shared Base for all ORM models)
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Single shared Declarative Base class for all SQLAlchemy ORM models."""
    pass


# ---------------------------------------------------------------------------
# Load .env from project root
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
_ENV_PATH = PROJECT_ROOT / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()


def _get_env(key: str, default: str = "") -> str:
    return os.getenv(key, default).strip()


# Pool settings
DB_POOL_SIZE = int(_get_env("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(_get_env("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(_get_env("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(_get_env("DB_POOL_RECYCLE", "1800"))

is_render = bool(os.getenv("RENDER")) or os.getenv("RENDER_SERVICE_ID") is not None
is_prod = _get_env("APP_ENV").lower() == "production" or is_render


def _build_pg_url() -> str:
    """Build or normalize PostgreSQL connection URL from environment variables."""
    raw_url = _get_env("DATABASE_URL")
    if raw_url:
        # Render provides postgres:// which SQLAlchemy 2.0 requires as postgresql://
        url = raw_url.replace("postgres://", "postgresql://", 1)
        if url.startswith("postgresql://") and not url.startswith("postgresql+"):
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url

    # Fallback to individual PG* environment variables
    pg_host = _get_env("PGHOST", _get_env("POSTGRES_HOST", "localhost"))
    pg_port = _get_env("PGPORT", _get_env("POSTGRES_PORT", "5433"))
    pg_db = _get_env("PGDATABASE", _get_env("POSTGRES_DB", "heartmortality"))
    pg_user = _get_env("PGUSER", _get_env("POSTGRES_USER", "postgres"))
    pg_pass = _get_env("PGPASSWORD", _get_env("POSTGRES_PASSWORD", ""))

    if pg_host and pg_db and pg_user:
        encoded_pass = urllib.parse.quote_plus(pg_pass)
        auth = f"{pg_user}:{encoded_pass}@" if pg_pass else f"{pg_user}@"
        return f"postgresql+psycopg2://{auth}{pg_host}:{pg_port}/{pg_db}"

    return ""


# ---------------------------------------------------------------------------
# SQLAlchemy Engine Initialization (PostgreSQL Primary)
# ---------------------------------------------------------------------------
engine = None
DATABASE_URL = None
DB_DATABASE = "heartmortality"
DB_SERVER = "PostgreSQL"

_pg_url = _build_pg_url()

if _pg_url:
    try:
        # Fast probe with short timeout to detect reachability
        _probe_engine = create_engine(
            _pg_url,
            connect_args={"connect_timeout": 3},
        )
        with _probe_engine.connect() as _probe_conn:
            _probe_conn.execute(text("CREATE SCHEMA IF NOT EXISTS clinical"))
            _probe_conn.commit()
            _probe_conn.execute(text("SELECT 1"))
        _probe_engine.dispose()

        # Connect full engine with search_path set to clinical,public
        engine = create_engine(
            _pg_url,
            connect_args={"options": "-c search_path=clinical,public"},
            pool_size=DB_POOL_SIZE,
            max_overflow=DB_MAX_OVERFLOW,
            pool_timeout=DB_POOL_TIMEOUT,
            pool_recycle=DB_POOL_RECYCLE,
            pool_pre_ping=True,
        )
        DATABASE_URL = _pg_url
        logger.info(f"Connected successfully to PostgreSQL database ({_pg_url.split('@')[-1] if '@' in _pg_url else 'local'})")
    except Exception as _pg_err:
        logger.error(f"PostgreSQL connection failed: {_pg_err}")
        if is_prod:
            raise RuntimeError(f"FATAL: Production requires PostgreSQL DATABASE_URL. Connection failed: {_pg_err}") from _pg_err
        engine = None

if engine is None:
    if is_prod:
        raise RuntimeError("FATAL: Production requires PostgreSQL DATABASE_URL. SQLite/MSSQL are strictly forbidden in production.")

    _allow_sqlite = _get_env("ALLOW_SQLITE_OFFLINE", "true").lower() in ("true", "1", "yes")
    if not _allow_sqlite:
        raise RuntimeError(
            "FATAL: PostgreSQL connection failed to localhost:5433 (heartmortality). "
            "Silent fallback to SQLite is disabled to prevent accidental SQLite usage in development. "
            "To allow offline sandbox testing, set ALLOW_SQLITE_OFFLINE=true."
        )

    # Offline development fallback strictly for sandboxed automated testing
    sqlite_db_path = PROJECT_ROOT / "clinical_local.db"
    DATABASE_URL = f"sqlite:///{sqlite_db_path.as_posix()}"
    logger.warning("Active fallback: PostgreSQL unavailable and ALLOW_SQLITE_OFFLINE=true; initializing SQLite (clinical_local.db).")
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

    # In SQLite, strip 'clinical' schema prefix
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
    Accurately identifies whether PostgreSQL or SQLite is currently active.
    """
    if engine is None:
        return {
            "status": "error",
            "database": "none",
            "dialect": "none",
            "message": "SQLAlchemy engine is not initialized.",
        }

    try:
        with engine.connect() as conn:
            if conn.dialect.name == "postgresql":
                db_name = conn.execute(text("SELECT current_database()")).scalar()
                return {
                    "status": "connected",
                    "database": db_name or "heartmortality",
                    "dialect": "postgresql",
                    "message": "PostgreSQL database connection verified (schema: clinical)",
                }
            elif conn.dialect.name == "sqlite":
                conn.execute(text("SELECT 1"))
                return {
                    "status": "connected",
                    "database": "clinical_local.db",
                    "dialect": "sqlite",
                    "message": "Offline fallback SQLite database active (clinical_local.db)",
                }
            else:
                conn.execute(text("SELECT 1"))
                return {
                    "status": "connected",
                    "database": "connected",
                    "dialect": conn.dialect.name,
                    "message": f"{conn.dialect.name} database connection verified",
                }
    except Exception as exc:
        return {
            "status": "disconnected",
            "database": DB_DATABASE,
            "dialect": engine.dialect.name if engine else "none",
            "message": f"Database connection failed: {str(exc)}",
        }
