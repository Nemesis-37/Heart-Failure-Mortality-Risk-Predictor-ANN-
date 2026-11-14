"""
database/ package initialization.

Exposes SQLAlchemy components from the root database.py file.
"""

import importlib.util
from pathlib import Path

_root_db_file = Path(__file__).resolve().parent.parent / "database.py"

if _root_db_file.exists():
    _spec = importlib.util.spec_from_file_location("root_database", _root_db_file)
    _mod = importlib.util.module_from_spec(_spec)
    _spec.loader.exec_module(_mod)

    engine = _mod.engine
    SessionLocal = _mod.SessionLocal
    Base = _mod.Base
    get_db = _mod.get_db
    test_db_connection = _mod.test_db_connection
else:
    from database.config import Base, SessionLocal, engine, get_db, test_connection as test_db_connection

__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "test_db_connection",
]
