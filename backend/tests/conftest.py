"""
Pytest configuration and fixtures for testing
"""
import pytest
import os
import tempfile
import shutil
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.database import Base, get_db
from fastapi.testclient import TestClient

# Import all models to ensure they are registered with Base
from environment_service import models as env_models
from project_service import models as project_models
from system_service import models as system_models
from audit_service import models as audit_models
from task_service import models as task_models

# Create a test database
TEST_DB_PATH = tempfile.mktemp(suffix=".db")
TEST_DATABASE_URL = f"sqlite:///{TEST_DB_PATH}"

@pytest.fixture(scope="function")
def test_db():
    """Create a test database for each test"""
    engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        engine.dispose()
        if os.path.exists(TEST_DB_PATH):
            os.remove(TEST_DB_PATH)

@pytest.fixture(scope="function")
def test_client(test_db):
    """Create a test client with test database"""
    # Import app here to avoid circular imports and ensure proper initialization
    from main import app
    
    def override_get_db():
        try:
            yield test_db
        finally:
            pass
    
    app.dependency_overrides[get_db] = override_get_db
    client = TestClient(app)
    yield client
    app.dependency_overrides.clear()

@pytest.fixture(scope="function")
def temp_dir():
    """Create a temporary directory for testing"""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)
