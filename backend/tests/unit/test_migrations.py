"""
Unit tests for migrations/manager.py
"""
import pytest
import os
import tempfile
import sqlite3
from migrations.manager import MigrationManager


@pytest.fixture
def temp_db():
    """Create a temporary database for testing"""
    temp_path = tempfile.mktemp(suffix=".db")
    yield temp_path
    if os.path.exists(temp_path):
        os.remove(temp_path)


def test_migration_manager_init(temp_db):
    """Test that MigrationManager initializes correctly"""
    manager = MigrationManager()
    manager.db_path = temp_db
    assert manager.db_path == temp_db
    assert manager.migrations_table == "schema_migrations"
    assert isinstance(manager.migrations, list)


def test_register_migration(temp_db):
    """Test that migrations can be registered"""
    manager = MigrationManager()
    manager.db_path = temp_db
    
    def test_migration(conn):
        pass
    
    manager.register_migration("001", "Test migration", test_migration)
    assert len(manager.migrations) == 1
    assert manager.migrations[0]["version"] == "001"
    assert manager.migrations[0]["description"] == "Test migration"


def test_ensure_migrations_table(temp_db):
    """Test that migrations table is created"""
    manager = MigrationManager()
    manager.db_path = temp_db
    
    # Create the database file first
    conn = sqlite3.connect(temp_db)
    conn.close()
    
    manager.ensure_migrations_table()
    
    # Check that table exists
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='schema_migrations'")
    result = cursor.fetchone()
    conn.close()
    
    assert result is not None


def test_get_applied_migrations(temp_db):
    """Test that applied migrations can be retrieved"""
    manager = MigrationManager()
    manager.db_path = temp_db
    
    # Create database and table
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE schema_migrations (
            version TEXT PRIMARY KEY,
            description TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    cursor.execute("INSERT INTO schema_migrations (version, description) VALUES (?, ?)", ("001", "Test"))
    conn.commit()
    conn.close()
    
    applied = manager.get_applied_migrations()
    assert "001" in applied


def test_mark_migration_applied(temp_db):
    """Test that migrations can be marked as applied"""
    manager = MigrationManager()
    manager.db_path = temp_db
    
    # Create database and table
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE schema_migrations (
            version TEXT PRIMARY KEY,
            description TEXT,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()
    
    manager.mark_migration_applied("002", "Test migration 2")
    
    # Check that migration was recorded
    conn = sqlite3.connect(temp_db)
    cursor = conn.cursor()
    cursor.execute("SELECT version FROM schema_migrations WHERE version = ?", ("002",))
    result = cursor.fetchone()
    conn.close()
    
    assert result is not None
    assert result[0] == "002"
