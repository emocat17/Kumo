"""
Unit tests for core/security.py
"""
import pytest
import os
import tempfile
import shutil
from pathlib import Path
from cryptography.fernet import Fernet
from core.security import get_key, get_cipher_suite, encrypt_value, decrypt_value
from core.config import Settings


def test_get_key_from_env():
    """Test that get_key reads from environment variable"""
    original_key = os.environ.get("KUMO_SECRET_KEY")
    try:
        test_key = Fernet.generate_key().decode()
        os.environ["KUMO_SECRET_KEY"] = test_key
        key = get_key()
        assert key == test_key.encode()
    finally:
        if original_key:
            os.environ["KUMO_SECRET_KEY"] = original_key
        elif "KUMO_SECRET_KEY" in os.environ:
            del os.environ["KUMO_SECRET_KEY"]


def test_get_key_from_file():
    """Test that get_key reads from file"""
    temp_dir = tempfile.mkdtemp()
    try:
        secret_key_file = Path(temp_dir) / "secret.key"
        test_key = Fernet.generate_key()
        secret_key_file.parent.mkdir(parents=True, exist_ok=True)
        secret_key_file.write_bytes(test_key)
        
        # Temporarily override settings
        from core.config import settings
        original_secret_key_file = settings.secret_key_file
        settings.secret_key_file = str(secret_key_file)
        
        # Clear environment variable to force file reading
        original_env_key = os.environ.get("KUMO_SECRET_KEY")
        if "KUMO_SECRET_KEY" in os.environ:
            del os.environ["KUMO_SECRET_KEY"]
        
        try:
            key = get_key()
            assert key == test_key
        finally:
            settings.secret_key_file = original_secret_key_file
            if original_env_key:
                os.environ["KUMO_SECRET_KEY"] = original_env_key
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_get_key_generates_new():
    """Test that get_key generates a new key if none exists"""
    temp_dir = tempfile.mkdtemp()
    try:
        secret_key_file = Path(temp_dir) / "secret.key"
        
        # Temporarily override settings
        from core.config import settings
        original_secret_key_file = settings.secret_key_file
        settings.secret_key_file = str(secret_key_file)
        
        # Clear environment variable and ensure file doesn't exist
        original_env_key = os.environ.get("KUMO_SECRET_KEY")
        if "KUMO_SECRET_KEY" in os.environ:
            del os.environ["KUMO_SECRET_KEY"]
        
        try:
            key = get_key()
            assert key is not None
            assert len(key) > 0
            # Verify key file was created
            assert secret_key_file.exists()
            # Verify key is valid Fernet key
            Fernet(key)  # Should not raise exception
        finally:
            settings.secret_key_file = original_secret_key_file
            if original_env_key:
                os.environ["KUMO_SECRET_KEY"] = original_env_key
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def test_get_cipher_suite():
    """Test that get_cipher_suite returns a Fernet instance"""
    cipher = get_cipher_suite()
    assert cipher is not None
    assert isinstance(cipher, Fernet)


def test_encrypt_decrypt():
    """Test that encrypt and decrypt work correctly"""
    test_value = "test_secret_value_123"
    encrypted = encrypt_value(test_value)
    
    assert encrypted != test_value
    assert len(encrypted) > 0
    
    decrypted = decrypt_value(encrypted)
    assert decrypted == test_value


def test_encrypt_empty_string():
    """Test that encrypting empty string returns empty string"""
    result = encrypt_value("")
    assert result == ""


def test_decrypt_empty_string():
    """Test that decrypting empty string returns empty string"""
    result = decrypt_value("")
    assert result == ""


def test_decrypt_invalid_token():
    """Test that decrypting invalid token returns original value"""
    invalid_token = "invalid_encrypted_token"
    result = decrypt_value(invalid_token)
    # Should return original value if decryption fails
    assert result == invalid_token


def test_encrypt_decrypt_special_characters():
    """Test that encrypt/decrypt handles special characters"""
    test_values = [
        "test@example.com",
        "password!@#$%^&*()",
        "中文测试",
        "test\nnewline\ttab",
        "test with spaces",
    ]
    
    for value in test_values:
        encrypted = encrypt_value(value)
        decrypted = decrypt_value(encrypted)
        assert decrypted == value


def test_encrypt_decrypt_unicode():
    """Test that encrypt/decrypt handles unicode characters"""
    test_value = "测试 🚀 émojis 中文"
    encrypted = encrypt_value(test_value)
    decrypted = decrypt_value(encrypted)
    assert decrypted == test_value
