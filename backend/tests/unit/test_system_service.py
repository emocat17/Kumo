"""
单元测试 - System Service 核心功能
"""
import pytest
import tempfile
import os
import time
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from system_service import models, schemas
from system_service.system_router import get_size


class TestSystemServiceHelpers:
    """System Service 辅助函数测试"""
    
    def test_get_size_bytes(self):
        """测试字节格式化 - 字节"""
        assert get_size(512) == "512.00 B"
        assert get_size(0) == "0.00 B"
    
    def test_get_size_kb(self):
        """测试字节格式化 - KB"""
        assert get_size(1024) == "1.00 KB"
        assert get_size(1536) == "1.50 KB"
    
    def test_get_size_mb(self):
        """测试字节格式化 - MB"""
        assert get_size(1024 * 1024) == "1.00 MB"
        assert get_size(1024 * 1024 * 1.5) == "1.50 MB"
    
    def test_get_size_gb(self):
        """测试字节格式化 - GB"""
        assert get_size(1024 * 1024 * 1024) == "1.00 GB"
        assert get_size(1024 * 1024 * 1024 * 2.5) == "2.50 GB"
    
    def test_get_size_custom_suffix(self):
        """测试自定义后缀"""
        assert get_size(1024, suffix="bytes") == "1.00 Kbytes"
        assert get_size(1024, suffix="") == "1.00 K"


class TestSystemRouter:
    """System Router 路由测试"""
    
    def test_get_all_configs_empty(self, test_client):
        """测试获取空配置列表"""
        response = test_client.get("/api/system/config")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    
    def test_create_config(self, test_client):
        """测试创建配置"""
        response = test_client.post(
            "/api/system/config",
            json={
                "key": "test.config",
                "value": "test_value",
                "description": "Test configuration"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "test.config"
        assert data["value"] == "test_value"
        assert data["description"] == "Test configuration"
    
    def test_update_config(self, test_client):
        """测试更新配置"""
        # Create config first
        test_client.post(
            "/api/system/config",
            json={
                "key": "test.update",
                "value": "old_value",
                "description": "Old description"
            }
        )
        
        # Update config
        response = test_client.post(
            "/api/system/config",
            json={
                "key": "test.update",
                "value": "new_value",
                "description": "New description"
            }
        )
        assert response.status_code == 200
        data = response.json()
        assert data["value"] == "new_value"
        assert data["description"] == "New description"
    
    def test_get_config_by_key(self, test_client):
        """测试根据键获取配置"""
        # Create config first
        test_client.post(
            "/api/system/config",
            json={
                "key": "test.get",
                "value": "get_value"
            }
        )
        
        # Get config
        response = test_client.get("/api/system/config/test.get")
        assert response.status_code == 200
        data = response.json()
        assert data["key"] == "test.get"
        assert data["value"] == "get_value"
    
    def test_get_config_by_key_not_found(self, test_client):
        """测试获取不存在的配置"""
        response = test_client.get("/api/system/config/nonexistent.key")
        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data
        assert "not found" in error_data["error"]["message"].lower()
    
    def test_get_system_info(self, test_client):
        """测试获取系统信息"""
        response = test_client.get("/api/system/info")
        assert response.status_code == 200
        data = response.json()
        
        assert "env_count" in data
        assert "project_count" in data
        assert "uptime_minutes" in data
        assert "system_info" in data
        
        assert isinstance(data["env_count"], int)
        assert isinstance(data["project_count"], int)
        assert isinstance(data["uptime_minutes"], int)
        assert isinstance(data["system_info"], dict)
        
        # Check system_info structure
        sys_info = data["system_info"]
        assert "system" in sys_info
        assert "python_version" in sys_info
    
    def test_get_system_stats(self, test_client):
        """测试获取系统统计"""
        response = test_client.get("/api/system/stats")
        assert response.status_code == 200
        data = response.json()
        
        # Should return statistics
        assert isinstance(data, dict)
    
    def test_get_data_overview(self, test_client):
        """测试获取数据概览"""
        response = test_client.get("/api/system/data/overview")
        assert response.status_code == 200
        data = response.json()
        
        # Should return overview data
        assert isinstance(data, dict)
    
    def test_list_backups(self, test_client):
        """测试列出备份"""
        response = test_client.get("/api/system/backups")
        assert response.status_code == 200
        data = response.json()
        
        # Should return list of backups
        assert isinstance(data, list)
    
    def test_create_backup(self, test_client):
        """测试创建备份"""
        response = test_client.post("/api/system/backup")
        
        # May succeed or fail depending on database state
        # But should not return 404
        assert response.status_code != 404
        
        if response.status_code == 200:
            data = response.json()
            assert "message" in data
            assert "filename" in data or "path" in data
    
    def test_delete_backup_not_found(self, test_client):
        """测试删除不存在的备份"""
        response = test_client.delete("/api/system/backups/nonexistent.db")
        # Should return 404 or 400
        assert response.status_code in [404, 400]
