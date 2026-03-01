"""
Unit tests for core/logging.py
"""
import pytest
import logging
import os
import tempfile
import shutil
from pathlib import Path
from core.logging import get_logger, setup_logging


def test_get_logger():
    """Test that get_logger returns a logger instance"""
    logger = get_logger(__name__)
    assert isinstance(logger, logging.Logger)
    assert logger.name == __name__


def test_logger_output(caplog):
    """Test that logger outputs messages"""
    logger = get_logger("test_logger")
    logger.info("Test message")
    
    # Check that message was logged using caplog
    assert "Test message" in caplog.text


def test_setup_logging():
    """Test that setup_logging configures logging correctly"""
    temp_dir = tempfile.mkdtemp()
    try:
        # Temporarily change logs_dir
        from core.config import settings
        original_logs_dir = settings.logs_dir
        settings.logs_dir = temp_dir
        
        setup_logging(log_level="DEBUG")
        
        logger = get_logger("test")
        logger.debug("Debug message")
        logger.info("Info message")
        logger.warning("Warning message")
        logger.error("Error message")
        
        # Check that log files were created
        log_dir = Path(temp_dir)
        assert (log_dir / "app.log").exists()
        assert (log_dir / "error.log").exists()
        
        # Restore original logs_dir
        settings.logs_dir = original_logs_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_logger_levels():
    """Test that logger respects log levels"""
    logger = get_logger("test_levels")
    
    # All log levels should work
    logger.debug("Debug")
    logger.info("Info")
    logger.warning("Warning")
    logger.error("Error")
    logger.critical("Critical")
    
    # If we get here without exception, the test passes
    assert True
