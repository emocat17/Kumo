"""
安全模块
提供加密解密功能，使用统一配置管理
"""
import os
from cryptography.fernet import Fernet
from core.logging import get_logger
from core.config import settings

logger = get_logger(__name__)


def get_key():
    """
    Load the secret key from environment variable or file.
    If not found, generate a new one and save it to file.
    
    Returns:
        bytes: 密钥字节串
    """
    # 1. Try environment variable (优先使用配置中的环境变量名)
    key = os.environ.get(settings.secret_key_env)
    if key:
        return key.encode()
    
    # 2. Try file (使用配置中的文件路径)
    secret_key_file = settings.secret_key_file
    if os.path.exists(secret_key_file):
        with open(secret_key_file, "rb") as key_file:
            return key_file.read()
    
    # 3. Generate new key
    key = Fernet.generate_key()
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(secret_key_file), exist_ok=True)
        with open(secret_key_file, "wb") as key_file:
            key_file.write(key)
        logger.info(f"Generated new secret key and saved to {secret_key_file}")
    except Exception as e:
        logger.warning(f"Could not save secret key to file: {e}")
    
    return key

_cipher_suite = None

def get_cipher_suite():
    global _cipher_suite
    if _cipher_suite is None:
        key = get_key()
        _cipher_suite = Fernet(key)
    return _cipher_suite

def encrypt_value(value: str) -> str:
    """
    加密字符串值
    
    Args:
        value: 要加密的字符串
        
    Returns:
        str: 加密后的字符串（base64编码）
    """
    if not value:
        return ""
    cipher = get_cipher_suite()
    encrypted_bytes = cipher.encrypt(value.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')


def decrypt_value(token: str) -> str:
    """
    解密加密的字符串令牌
    
    Args:
        token: 要解密的字符串（base64编码）
        
    Returns:
        str: 解密后的原始字符串，如果解密失败则返回原始值
    """
    if not token:
        return ""
    try:
        cipher = get_cipher_suite()
        decrypted_bytes = cipher.decrypt(token.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception as e:
        # Return original if decryption fails (e.g. key changed or not encrypted)
        logger.warning(f"Failed to decrypt value: {e}")
        return token
