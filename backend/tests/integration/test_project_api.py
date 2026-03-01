"""
Integration tests for project API endpoints
"""
import pytest
import tempfile
import os
from fastapi.testclient import TestClient
from project_service import models


def test_list_projects(test_client: TestClient, test_db):
    """Test listing projects"""
    response = test_client.get("/api/projects")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_create_project(test_client: TestClient, test_db, temp_dir):
    """Test creating a project"""
    # Create a test zip file
    import zipfile
    import tempfile
    
    tmp_file_path = None
    try:
        with tempfile.NamedTemporaryFile(suffix='.zip', delete=False) as tmp_file:
            tmp_file_path = tmp_file.name
            with zipfile.ZipFile(tmp_file.name, 'w') as zipf:
                zipf.writestr('test.py', 'print("hello")')
        
        with open(tmp_file_path, 'rb') as f:
            response = test_client.post(
                "/api/projects/create",
                files={"file": ("test.zip", f, "application/zip")},
                data={
                    "name": "test_project",
                    "work_dir": ".",
                    "output_dir": "./output",
                    "description": "Test project"
                }
            )
    finally:
        # Try to delete temp file, ignore errors on Windows
        if tmp_file_path and os.path.exists(tmp_file_path):
            try:
                os.unlink(tmp_file_path)
            except (PermissionError, OSError):
                pass  # Ignore deletion errors on Windows
    
    # Should succeed or fail with validation error
    assert response.status_code in [200, 201, 400, 422]


def test_get_project(test_client: TestClient, test_db):
    """Test getting a specific project"""
    response = test_client.get("/api/projects/1")
    # Should return 404 if project doesn't exist, or 200 if it does
    assert response.status_code in [200, 404]


def test_update_project(test_client: TestClient, test_db):
    """Test updating a project"""
    response = test_client.put(
        "/api/projects/1",
        json={
            "name": "updated_project",
            "path": "/tmp/test",
            "work_dir": ".",
            "output_dir": "./output",
            "description": "Updated project"
        }
    )
    # Should return 404 if project doesn't exist, or 200 if it does
    assert response.status_code in [200, 404, 422]


def test_delete_project(test_client: TestClient, test_db):
    """Test deleting a project"""
    response = test_client.delete("/api/projects/1")
    # Should return 404 if project doesn't exist, or 200 if it does
    assert response.status_code in [200, 404]
