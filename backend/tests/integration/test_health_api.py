"""
Integration tests for health check and version API endpoints
"""
import pytest
from fastapi.testclient import TestClient


def test_health_check(test_client: TestClient):
    """Test health check endpoint"""
    response = test_client.get("/api/health")
    assert response.status_code in [200, 503]  # 503 if scheduler not started in test
    data = response.json()
    assert "status" in data
    assert "database" in data
    assert "scheduler" in data


def test_version_endpoint(test_client: TestClient):
    """Test version endpoint"""
    response = test_client.get("/api/version")
    assert response.status_code == 200
    data = response.json()
    assert "version" in data
    assert "name" in data
    assert data["name"] == "Kumo"
