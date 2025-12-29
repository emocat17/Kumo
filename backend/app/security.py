import os
from cryptography.fernet import Fernet

# Define path for secret key
SECRET_KEY_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data", "secret.key")

def get_key():
    """
    Load the secret key from environment variable or file.
    If not found, generate a new one and save it to file.
    """
    # 1. Try environment variable
    key = os.environ.get("KUMO_SECRET_KEY")
    if key:
        return key.encode()
    
    # 2. Try file
    if os.path.exists(SECRET_KEY_FILE):
        with open(SECRET_KEY_FILE, "rb") as key_file:
            return key_file.read()
    
    # 3. Generate new key
    key = Fernet.generate_key()
    try:
        # Ensure directory exists
        os.makedirs(os.path.dirname(SECRET_KEY_FILE), exist_ok=True)
        with open(SECRET_KEY_FILE, "wb") as key_file:
            key_file.write(key)
    except Exception as e:
        print(f"Warning: Could not save secret key to file: {e}")
    
    return key

_cipher_suite = None

def get_cipher_suite():
    global _cipher_suite
    if _cipher_suite is None:
        key = get_key()
        _cipher_suite = Fernet(key)
    return _cipher_suite

def encrypt_value(value: str) -> str:
    """Encrypts a string value."""
    if not value:
        return ""
    cipher = get_cipher_suite()
    encrypted_bytes = cipher.encrypt(value.encode('utf-8'))
    return encrypted_bytes.decode('utf-8')

def decrypt_value(token: str) -> str:
    """Decrypts an encrypted string token."""
    if not token:
        return ""
    try:
        cipher = get_cipher_suite()
        decrypted_bytes = cipher.decrypt(token.encode('utf-8'))
        return decrypted_bytes.decode('utf-8')
    except Exception:
        # Return original if decryption fails (e.g. key changed or not encrypted)
        # In production, we might want to log this error
        return token
