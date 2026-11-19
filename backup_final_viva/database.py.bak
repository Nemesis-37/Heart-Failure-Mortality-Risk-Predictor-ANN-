"""
database.py (Compatibility Layer)
=================================
Forwards all database engine, session, Base, and model dependencies directly
to the centralized configuration in backend/database/.

This file ensures that any external tool or script expecting root 'database.py'
shares the exact same engine, SessionLocal, Base, and models without duplication.
"""

from backend.database.config import (
    Base,
    DATABASE_URL,
    DB_DATABASE,
    DB_SERVER,
    SessionLocal,
    engine,
    get_db,
    test_connection,
    test_db_connection,
)
import backend.database.models as models

__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "test_connection",
    "test_db_connection",
    "DATABASE_URL",
    "DB_DATABASE",
    "DB_SERVER",
    "models",
]
