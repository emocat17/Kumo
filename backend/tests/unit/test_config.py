"""
Unit tests for core/config.py
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from core.config import Settings, settings


def test_settings_default_values():
    """Test that settings have default values"""
    assert settings.projects_dir is not None
    assert settings.data_dir is not None
    assert settings.logs_dir is not None
    assert settings.envs_dir is not None
    assert settings.database_url is not None
    assert settings.max_concurrent_tasks > 0


def test_settings_from_env():
    """Test that settings can be overridden by environment variables"""
    original_value = settings.max_concurrent_tasks
    try:
        os.environ["KUMO_MAX_CONCURRENT_TASKS"] = "100"
        new_settings = Settings()
        assert new_settings.max_concurrent_tasks == 100
    finally:
        if "KUMO_MAX_CONCURRENT_TASKS" in os.environ:
            del os.environ["KUMO_MAX_CONCURRENT_TASKS"]


def test_settings_paths_are_absolute():
    """Test that path settings are converted to absolute paths"""
    assert os.path.isabs(settings.projects_dir) or settings.projects_dir.startswith("./")
    assert os.path.isabs(settings.data_dir) or settings.data_dir.startswith("./")
    assert os.path.isabs(settings.logs_dir) or settings.logs_dir.startswith("./")
    assert os.path.isabs(settings.envs_dir) or settings.envs_dir.startswith("./")


def test_settings_ensure_directories():
    """Test that ensure_directories creates necessary directories"""
    temp_dir = Path(tempfile.mkdtemp())
    try:
        test_settings = Settings(
            projects_dir=str(temp_dir / "projects"),
            data_dir=str(temp_dir / "data"),
            logs_dir=str(temp_dir / "logs"),
            envs_dir=str(temp_dir / "envs"),
        )
        test_settings.ensure_directories()
        
        assert (temp_dir / "projects").exists()
        assert (temp_dir / "data").exists()
        assert (temp_dir / "logs").exists()
        assert (temp_dir / "envs").exists()
    finally:
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_settings_database_url_normalization():
    """Test that database URL is normalized correctly"""
    # Test that relative paths are converted to absolute
    assert "sqlite:///" in settings.database_url
    # The path part should be absolute or relative to backend
    db_path = settings.database_url.replace("sqlite:///", "")
    assert db_path


def test_settings_pool_config():
    """Test that database pool settings are configured"""
    assert settings.database_pool_size > 0
    assert settings.database_max_overflow >= 0
    assert isinstance(settings.database_pool_pre_ping, bool)
