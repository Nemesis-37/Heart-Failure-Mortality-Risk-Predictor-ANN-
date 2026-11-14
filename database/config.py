"""
database/config.py
==================
SQLAlchemy engine, session factory, and declarative Base for the
Heart Failure Mortality Risk Predictor.

This module reads connection settings from environment variables
(loaded from .env by python-dotenv) and builds a reusable
SQLAlchemy 2.x engine and session factory.

Usage
-----
    from database.config import get_db, Base

    # In a FastAPI route:
    def my_route(db: Session = Depends(get_db)):
        ...

    # In an Alembic env.py:
    from database.config import Base
    target_metadata = Base.metadata
"""

import os
import urllib
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker

# ---------------------------------------------------------------------------
# Load .env from the project root (one level up from this file)
# ---------------------------------------------------------------------------
_ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=_ENV_PATH)


# ---------------------------------------------------------------------------
# Read connection settings from environment variables
# ---------------------------------------------------------------------------

def _get_env(key: str, default: str = "") -> str:
    """Return the value of an environment variable, stripped of whitespace."""
    return os.getenv(key, default).strip()


DB_SERVER = _get_env("DB_SERVER", "localhost")
DB_INSTANCE = _get_env("DB_INSTANCE", "SQLEXPRESS")
DB_NAME = _get_env("DB_NAME", "HeartFailureDB")
DB_AUTH_MODE = _get_env("DB_AUTH_MODE", "windows").lower()
DB_USERNAME = _get_env("DB_USERNAME")
DB_PASSWORD = _get_env("DB_PASSWORD")
DB_DRIVER = _get_env("DB_DRIVER", "ODBC Driver 18 for SQL Server")
DB_TRUST_CERT = _get_env("DB_TRUST_SERVER_CERTIFICATE", "yes")

DB_POOL_SIZE = int(_get_env("DB_POOL_SIZE", "5"))
DB_MAX_OVERFLOW = int(_get_env("DB_MAX_OVERFLOW", "10"))
DB_POOL_TIMEOUT = int(_get_env("DB_POOL_TIMEOUT", "30"))
DB_POOL_RECYCLE = int(_get_env("DB_POOL_RECYCLE", "1800"))


# ---------------------------------------------------------------------------
# Build the ODBC connection string
# ---------------------------------------------------------------------------

def _build_connection_string() -> str:
    """
    Build a pyodbc connection string from environment variables.

    Supports:
    - Windows Authentication  (DB_AUTH_MODE=windows)
    - SQL Server Authentication (DB_AUTH_MODE=sql)

    Returns a URL-encoded string ready for SQLAlchemy's
    mssql+pyodbc:///?odbc_connect=... driver.
    """
    # The server address — combine host and named instance if provided
    if DB_INSTANCE:
        server = f"{DB_SERVER}\\{DB_INSTANCE}"
    else:
        server = DB_SERVER

    # Base ODBC parameters
    params = {
        "Driver": DB_DRIVER,
        "Server": server,
        "Database": DB_NAME,
        "TrustServerCertificate": DB_TRUST_CERT,
        "Encrypt": "yes",        # Always request an encrypted channel
        "Connection Timeout": "30",
    }

    # Authentication
    if DB_AUTH_MODE == "windows":
        # Windows Authentication — no username or password required
        params["Trusted_Connection"] = "yes"
    elif DB_AUTH_MODE == "sql":
        # SQL Server Authentication — requires username and password
        if not DB_USERNAME or not DB_PASSWORD:
            raise ValueError(
                "DB_USERNAME and DB_PASSWORD must be set when DB_AUTH_MODE=sql. "
                "Check your .env file."
            )
        params["UID"] = DB_USERNAME
        params["PWD"] = DB_PASSWORD
    else:
        raise ValueError(
            f"Unknown DB_AUTH_MODE='{DB_AUTH_MODE}'. "
            "Use 'windows' or 'sql' in your .env file."
        )

    # URL-encode the ODBC connection string for SQLAlchemy
    odbc_string = ";".join(f"{k}={v}" for k, v in params.items())
    return f"mssql+pyodbc:///?odbc_connect={urllib.parse.quote_plus(odbc_string)}"


# ---------------------------------------------------------------------------
# Create the SQLAlchemy engine
# ---------------------------------------------------------------------------

DATABASE_URL = _build_connection_string()

engine = create_engine(
    DATABASE_URL,
    # Pool settings
    pool_size=DB_POOL_SIZE,
    max_overflow=DB_MAX_OVERFLOW,
    pool_timeout=DB_POOL_TIMEOUT,
    pool_recycle=DB_POOL_RECYCLE,
    # Echo SQL statements only in development (set to False in production)
    echo=False,
    # Required for SQL Server — do not change
    fast_executemany=True,
)


# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------

SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


# ---------------------------------------------------------------------------
# Declarative Base — all ORM models inherit from this
# ---------------------------------------------------------------------------

class Base(DeclarativeBase):
    """
    Base class for all SQLAlchemy ORM models.

    Usage::

        from database.config import Base

        class MyModel(Base):
            __tablename__ = "my_table"
            ...
    """
    pass


# ---------------------------------------------------------------------------
# FastAPI dependency — provides a database session per request
# ---------------------------------------------------------------------------

def get_db():
    """
    FastAPI dependency that yields a SQLAlchemy session.

    Opens a session at the start of a request and closes it when the
    request finishes (whether it succeeded or raised an exception).

    Usage in a FastAPI route::

        from sqlalchemy.orm import Session
        from fastapi import Depends
        from database.config import get_db

        @app.get("/example")
        def example_route(db: Session = Depends(get_db)):
            result = db.execute(text("SELECT 1")).scalar()
            return {"result": result}
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Convenience helper — test the connection without starting FastAPI
# ---------------------------------------------------------------------------

def test_connection() -> bool:
    """
    Attempt a simple SELECT 1 query to verify the database connection.

    Returns True if successful, raises an exception otherwise.
    Called by scripts/test_db_connection.py.
    """
    with engine.connect() as conn:
        result = conn.execute(text("SELECT 1 AS connection_ok")).scalar()
        return result == 1
