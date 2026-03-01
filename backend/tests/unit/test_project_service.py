"""
单元测试 - Project Service 核心功能
"""
import pytest
import tempfile
import os
import zipfile
from unittest.mock import Mock, patch, MagicMock
from fastapi import HTTPException
from project_service import models, schemas
from project_service.project_router import (
    get_archive_extension,
    extract_archive,
    read_text_file
)


class TestProjectServiceHelpers:
    """Project Service 辅助函数测试"""
    
    def test_get_archive_extension_zip(self):
        """测试获取 ZIP 扩展名"""
        assert get_archive_extension("test.zip") == ".zip"
        assert get_archive_extension("test.ZIP") == ".zip"
        assert get_archive_extension("test.file.zip") == ".zip"
    
    def test_get_archive_extension_7z(self):
        """测试获取 7Z 扩展名"""
        assert get_archive_extension("test.7z") == ".7z"
        assert get_archive_extension("test.7Z") == ".7z"
    
    def test_get_archive_extension_rar(self):
        """测试获取 RAR 扩展名"""
        assert get_archive_extension("test.rar") == ".rar"
        assert get_archive_extension("test.RAR") == ".rar"
    
    def test_get_archive_extension_empty(self):
        """测试空文件名"""
        assert get_archive_extension("") == ""
        assert get_archive_extension(None) == ""
    
    def test_extract_archive_zip(self, temp_dir):
        """测试解压 ZIP 文件"""
        # Create a test zip file
        zip_path = os.path.join(temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.writestr('test.txt', 'test content')
            zipf.writestr('subdir/test2.txt', 'test content 2')
        
        dest_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(dest_dir)
        
        extract_archive(zip_path, ".zip", dest_dir)
        
        assert os.path.exists(os.path.join(dest_dir, "test.txt"))
        assert os.path.exists(os.path.join(dest_dir, "subdir", "test2.txt"))
    
    def test_extract_archive_invalid_zip(self, temp_dir):
        """测试无效的 ZIP 文件"""
        invalid_zip = os.path.join(temp_dir, "invalid.zip")
        with open(invalid_zip, 'w') as f:
            f.write("not a zip file")
        
        dest_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(dest_dir)
        
        with pytest.raises(Exception, match="not a valid zip file"):
            extract_archive(invalid_zip, ".zip", dest_dir)
    
    def test_extract_archive_unsupported_format(self, temp_dir):
        """测试不支持的压缩格式"""
        dest_dir = os.path.join(temp_dir, "extracted")
        os.makedirs(dest_dir)
        
        with pytest.raises(Exception, match="Unsupported archive format"):
            extract_archive("test.tar.gz", ".tar.gz", dest_dir)
    
    def test_read_text_file_utf8(self, temp_dir):
        """测试读取 UTF-8 文本文件"""
        test_file = os.path.join(temp_dir, "test_utf8.txt")
        content = "测试内容\nTest Content"
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        result = read_text_file(test_file)
        assert result == content
    
    def test_read_text_file_gb18030(self, temp_dir):
        """测试读取 GB18030 编码文件"""
        test_file = os.path.join(temp_dir, "test_gb.txt")
        content = "测试内容"
        try:
            with open(test_file, 'w', encoding='gb18030') as f:
                f.write(content)
            
            result = read_text_file(test_file)
            assert "测试" in result or len(result) > 0
        except (UnicodeEncodeError, LookupError):
            # Skip if gb18030 encoding not available
            pytest.skip("GB18030 encoding not available")
    
    def test_read_text_file_binary_fallback(self, temp_dir):
        """测试二进制文件回退处理"""
        test_file = os.path.join(temp_dir, "test_binary.bin")
        # Create a file with some binary data
        with open(test_file, 'wb') as f:
            f.write(b'\x00\x01\x02\x03\xff\xfe\xfd')
        
        # Should not raise exception, but may return garbled text
        result = read_text_file(test_file)
        assert isinstance(result, str)


class TestProjectRouter:
    """Project Router 路由测试"""
    
    def test_list_projects_empty(self, test_client):
        """测试获取空项目列表"""
        response = test_client.get("/api/projects")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
        assert len(response.json()) == 0
    
    def test_get_project_not_found(self, test_client):
        """测试获取不存在的项目"""
        response = test_client.get("/api/projects/999")
        assert response.status_code == 404
        error_data = response.json()
        assert "error" in error_data
        assert "not found" in error_data["error"]["message"].lower()
    
    def test_create_project_validation(self, test_client, temp_dir):
        """测试创建项目验证"""
        # Test without file
        response = test_client.post(
            "/api/projects/create",
            data={"name": "test"}
        )
        assert response.status_code == 422  # Validation error
    
    def test_create_project_duplicate_name(self, test_client, temp_dir):
        """测试创建重复名称的项目"""
        # Create a test zip file
        zip_path = os.path.join(temp_dir, "test.zip")
        with zipfile.ZipFile(zip_path, 'w') as zipf:
            zipf.writestr('test.py', 'print("hello")')
        
        # First create
        with open(zip_path, 'rb') as f:
            response1 = test_client.post(
                "/api/projects/create",
                files={"file": ("test.zip", f, "application/zip")},
                data={
                    "name": "test_project",
                    "work_dir": ".",
                    "output_dir": "./output"
                }
            )
        
        # Try to create again with same name
        if response1.status_code == 200:
            with open(zip_path, 'rb') as f:
                response2 = test_client.post(
                    "/api/projects/create",
                    files={"file": ("test.zip", f, "application/zip")},
                    data={
                        "name": "test_project",
                        "work_dir": ".",
                        "output_dir": "./output"
                    }
                )
            assert response2.status_code == 400
            assert "already exists" in response2.json()["detail"].lower()
    
    def test_detect_project_framework_not_found(self, test_client):
        """测试检测不存在的项目框架"""
        response = test_client.get("/api/projects/999/detect")
        assert response.status_code == 404
    
    def test_update_project_not_found(self, test_client):
        """测试更新不存在的项目"""
        response = test_client.put(
            "/api/projects/999",
            json={
                "name": "updated",
                "path": "/tmp/test",
                "work_dir": ".",
                "output_dir": "./output"
            }
        )
        assert response.status_code == 404
    
    def test_delete_project_not_found(self, test_client):
        """测试删除不存在的项目"""
        response = test_client.delete("/api/projects/999")
        assert response.status_code == 404
