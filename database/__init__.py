"""
database/
=========
Database layer for the Heart Failure Mortality Risk Predictor.

Exports
-------
- engine       : SQLAlchemy engine connected to SQL Server
- SessionLocal : Session factory for creating database sessions
- Base         : Declarative base class for ORM models
- get_db       : FastAPI dependency for per-request sessions
"""

from database.config import Base, SessionLocal, engine, get_db, test_connection

__all__ = [
    "engine",
    "SessionLocal",
    "Base",
    "get_db",
    "test_connection",
]
