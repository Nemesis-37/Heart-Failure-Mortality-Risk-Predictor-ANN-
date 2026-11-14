"""
database.py
===========
Microsoft SQL Server Express Database Configuration for FastAPI.

Features:
- SQLAlchemy engine configured for Microsoft SQL Server via ODBC Driver 18
- Windows Authentication (Trusted_Connection=yes)
- Connection parameters retrieved from environment variables (python-dotenv)
- SQLAlchemy URL.create() with URL-encoded ODBC connection string
- Configurable connection pooling (pool_size, max_overflow, pool_timeout, pool_recycle, pool_pre_ping)
- Thread-safe SessionLocal session factory
- Declarative Base for ORM models
- get_db session dependency with auto-cleanup and rollback on error
- Connection error handling
"""

import logging
import os
from pathlib import Path
from typing import Generator
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import DeclarativeBase, sessionmaker

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 1. Load environment variables from .env
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent
_ENV_PATH = BASE_DIR / ".env"
if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    load_dotenv()  # Fallback to current working directory or system environment

# ---------------------------------------------------------------------------
# 2. Retrieve connection settings from environment (no hardcoded credentials)
# ---------------------------------------------------------------------------
DB_DRIVER = os.getenv("DRIVER", os.getenv("DB_DRIVER", "{ODBC Driver 18 for SQL Server}")).strip()
DB_SERVER = os.getenv("SERVER", os.getenv("DB_SERVER", r".\SQLEXPRESS")).strip()
DB_DATABASE = os.getenv("DATABASE", os.getenv("DB_NAME", os.getenv("DB_DATABASE", "HeartMortalityPredictor"))).strip()
DB_TRUSTED_CONNECTION = os.getenv("Trusted_Connection", os.getenv("DB_TRUSTED_CONNECTION", "yes")).strip()
DB_ENCRYPT = os.getenv("Encrypt", os.getenv("DB_ENCRYPT", "yes")).strip()
DB_TRUST_SERVER_CERTIFICATE = os.getenv(
    "TrustServerCertificate", os.getenv("DB_TRUST_SERVER_CERTIFICATE", "yes")
).strip()

# Format driver with enclosing braces if omitted
clean_driver = DB_DRIVER.strip("{}")
formatted_driver = f"{{{clean_driver}}}"

# Construct ODBC connection string
odbc_connection_string = (
    f"DRIVER={formatted_driver};"
    f"SERVER={DB_SERVER};"
    f"DATABASE={DB_DATABASE};"
    f"Trusted_Connection={DB_TRUSTED_CONNECTION};"
    f"Encrypt={DB_ENCRYPT};"
    f"TrustServerCertificate={DB_TRUST_SERVER_CERTIFICATE};"
)

# ---------------------------------------------------------------------------
# 3. Connection Pooling Settings
# ---------------------------------------------------------------------------
DB_POOL_SIZE = int(os.getenv("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(os.getenv("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(os.getenv("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(os.getenv("DB_POOL_RECYCLE", "1800"))

# Build SQLAlchemy connection URL
DATABASE_URL = URL.create(
    "mssql+pyodbc",
    query={"odbc_connect": odbc_connection_string},
)

# ---------------------------------------------------------------------------
# 4. SQLAlchemy Engine Initialization with Connection Pooling & Error Handling
# ---------------------------------------------------------------------------
engine = None

try:
    import pyodbc  # Check if pyodbc is installed
    engine = create_engine(
        DATABASE_URL,
        pool_size=DB_POOL_SIZE,
        max_overflow=DB_MAX_OVERFLOW,
        pool_timeout=DB_POOL_TIMEOUT,
        pool_recycle=DB_POOL_RECYCLE,
        pool_pre_ping=True,  # Proactively test connection liveliness before checkout
        echo=False,
    )
except ImportError:
    logger.warning(
        "pyodbc is not installed in the virtual environment. "
        "Run 'pip install pyodbc' to connect to Microsoft SQL Server Express."
    )
except Exception as exc:
    logger.error(f"Error configuring SQLAlchemy engine: {exc}")

if engine is None:
    # Graceful development fallback when pyodbc/ODBC Driver 18 is not present
    try:
        engine = create_engine(
            "sqlite:///./clinical_local.db",
            connect_args={"check_same_thread": False},
            echo=False,
        )
    except Exception as _fb_err:
        logger.error(f"Fallback database engine error: {_fb_err}")


# ---------------------------------------------------------------------------
# 5. SessionLocal Session Factory
# ---------------------------------------------------------------------------
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)


# ---------------------------------------------------------------------------
# 6. Declarative Base
# ---------------------------------------------------------------------------
class Base(DeclarativeBase):
    """Declarative Base class for SQLAlchemy ORM models."""
    pass


# ---------------------------------------------------------------------------
# 7. Database Session Dependency
# ---------------------------------------------------------------------------
def get_db() -> Generator:
    """
    FastAPI dependency that yields a SQLAlchemy database session per request.
    Automatically handles rollback on error and ensures the session is closed.
    """
    if engine is None:
        raise RuntimeError("Database engine is not initialized. Please verify your SQL Server configuration and pyodbc installation.")

    db = SessionLocal()
    try:
        yield db
    except SQLAlchemyError as exc:
        db.rollback()
        logger.error(f"Database transaction error: {exc}")
        raise
    finally:
        db.close()


def test_db_connection() -> dict:
    """
    Utility function to test database connectivity by executing SELECT DB_NAME().
    Returns status dictionary.
    """
    try:
        import pyodbc  # noqa: F401
    except ImportError:
        return {
            "status": "error",
            "database": DB_DATABASE,
            "message": "Missing required dependency 'pyodbc'. Run: pip install pyodbc to connect to Microsoft SQL Server Express.",
        }

    if engine is None:
        return {
            "status": "error",
            "database": DB_DATABASE,
            "message": "SQLAlchemy engine could not be initialized with SQL Server parameters.",
        }

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT DB_NAME()")).scalar()
            return {
                "status": "connected",
                "database": result or DB_DATABASE,
                "message": "Database connection successful",
            }
    except Exception as exc:
        return {
            "status": "disconnected",
            "database": DB_DATABASE,
            "message": f"Connection failed: {str(exc)}",
        }
