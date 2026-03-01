"""
Unit tests for core/database.py
"""
import pytest
from sqlalchemy.orm import Session
from core.database import get_db, SessionLocal, engine

def test_get_db():
    """Test that get_db returns a database session"""
    db_gen = get_db()
    db = next(db_gen)
    assert isinstance(db, Session)
    db_gen.close()

def test_database_connection():
    """Test that database connection works"""
    from sqlalchemy import text
    db = SessionLocal()
    try:
        result = db.execute(text("SELECT 1"))
        assert result.scalar() == 1
    finally:
        db.close()

def test_engine_pool_config():
    """Test that engine has connection pool configured"""
    assert engine.pool is not None
    assert engine.pool.size() >= 0
