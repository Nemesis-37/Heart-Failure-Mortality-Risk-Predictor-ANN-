"""
backend/database/__init__.py
============================
Public API for the centralized database package.
Exports SQLAlchemy engine, SessionLocal, Base, get_db, and test helpers directly
from backend.database.config without any dynamic imports of root database.py.
"""

from backend.database.config import (
    Base,
    SessionLocal,
    engine,
    get_db,
    test_connection,
    test_db_connection,
)

__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "test_connection",
    "test_db_connection",
]
