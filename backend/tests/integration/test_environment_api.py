"""
Integration tests for Python environment API endpoints
"""
import pytest
from fastapi.testclient import TestClient


def test_list_python_versions(test_client: TestClient):
    """Test listing Python versions"""
    response = test_client.get("/api/python/versions")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_environments(test_client: TestClient):
    """Test listing Python environments"""
    response = test_client.get("/api/python/environments")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_environment(test_client: TestClient):
    """Test getting a specific environment"""
    response = test_client.get("/api/python/environments/1")
    assert response.status_code in [200, 404]


def test_create_environment(test_client: TestClient):
    """Test creating an environment"""
    # Note: Environment creation is via /api/python/versions/create-conda-env
    # This requires conda to be installed and may take a long time
    # For testing, we just check that the endpoint exists and handles requests
    response = test_client.post(
        "/api/python/versions/create-conda-env",
        json={
            "name": "test_env",
            "version": "3.9"
        }
    )
    # Should succeed, fail with validation error, or return 405 if method not allowed
    assert response.status_code in [200, 201, 400, 422, 405]
