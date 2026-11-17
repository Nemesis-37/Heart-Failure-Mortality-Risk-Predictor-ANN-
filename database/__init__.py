"""
database/__init__.py (Compatibility Layer)
==========================================
Forwards all imports directly to backend.database.
"""

from backend.database import (
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
