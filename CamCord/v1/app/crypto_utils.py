from cryptography.fernet import Fernet, InvalidToken
from typing import Optional
import os # For __main__ example if needed

def get_fernet_instance(key_string: Optional[str]) -> Optional[Fernet]:
    """Initializes and returns a Fernet instance from a base64 encoded key string."""
    if not key_string:
        return None
    try:
        key_bytes = key_string.encode()
        return Fernet(key_bytes)
    except Exception as e:
        print(f"Error initializing Fernet (key format may be invalid): {e}")
        return None

def encrypt_data(data: bytes, fernet: Fernet) -> Optional[bytes]:
    """Encrypts data using the provided Fernet instance."""
    try:
        return fernet.encrypt(data)
    except Exception as e:
        print(f"Error during encryption: {e}")
        return None

def decrypt_data(encrypted_data_token: bytes, fernet: Fernet) -> Optional[bytes]:
    """Decrypts data using the provided Fernet instance."""
    try:
        return fernet.decrypt(encrypted_data_token)
    except InvalidToken:
        print("Error during decryption: Invalid token (key mismatch or data corruption).")
        return None
    except Exception as e:
        print(f"Error during decryption: {e}")
        return None
