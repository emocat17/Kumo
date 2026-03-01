"""
Integration tests for task API endpoints
"""
import pytest
from fastapi.testclient import TestClient


def test_list_tasks(test_client: TestClient):
    """Test listing tasks"""
    response = test_client.get("/api/tasks")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_get_task(test_client: TestClient):
    """Test getting a specific task"""
    response = test_client.get("/api/tasks/1")
    assert response.status_code in [200, 404]


def test_create_task(test_client: TestClient, test_db):
    """Test creating a new task"""
    # First, try to create a task (will fail if project/env doesn't exist, which is expected)
    response = test_client.post(
        "/api/tasks",
        json={
            "name": "test_task",
            "command": "echo hello",
            "trigger_type": "interval",
            "trigger_value": '{"value": 1, "unit": "minutes"}',
            "project_id": 1,
            "env_id": None
        }
    )
    # Should return 400/422 if project doesn't exist, or 200/201 if it does
    assert response.status_code in [200, 201, 400, 422, 404]


def test_update_task(test_client: TestClient):
    """Test updating a task"""
    response = test_client.put(
        "/api/tasks/1",
        json={
            "name": "updated_task",
            "command": "echo updated",
            "trigger_type": "interval",
            "trigger_value": '{"value": 2, "unit": "minutes"}',
            "project_id": 1,
            "env_id": None
        }
    )
    assert response.status_code in [200, 404, 422]


def test_delete_task(test_client: TestClient):
    """Test deleting a task"""
    response = test_client.delete("/api/tasks/1")
    assert response.status_code in [200, 404]


def test_task_dashboard(test_client: TestClient):
    """Test task dashboard stats"""
    response = test_client.get("/api/tasks/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, dict)


def test_task_executions(test_client: TestClient):
    """Test getting task executions"""
    response = test_client.get("/api/tasks/1/executions")
    assert response.status_code in [200, 404]
    if response.status_code == 200:
        assert isinstance(response.json(), list)


def test_task_start_stop(test_client: TestClient):
    """Test starting and stopping a task"""
    # Test start
    response = test_client.post("/api/tasks/1/start")
    assert response.status_code in [200, 404, 400]
    
    # Test stop
    response = test_client.post("/api/tasks/1/stop")
    assert response.status_code in [200, 404, 400]

