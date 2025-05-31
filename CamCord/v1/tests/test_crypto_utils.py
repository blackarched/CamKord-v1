# CamCord/v1/tests/test_crypto_utils.py
import pytest
from cryptography.fernet import Fernet
from app.crypto_utils import get_fernet_instance, encrypt_data, decrypt_data

def test_fernet_instance_valid_key():
    key = Fernet.generate_key().decode()
    instance = get_fernet_instance(key)
    assert isinstance(instance, Fernet)

def test_fernet_instance_invalid_key():
    instance = get_fernet_instance("invalidkey")
    assert instance is None

def test_fernet_instance_none_key():
    instance = get_fernet_instance(None)
    assert instance is None

def test_encrypt_decrypt_roundtrip():
    key = Fernet.generate_key().decode()
    fernet = get_fernet_instance(key)
    assert fernet is not None
    original_data = b"test secret data for encryption"

    encrypted = encrypt_data(original_data, fernet)
    assert encrypted is not None
    assert encrypted != original_data

    decrypted = decrypt_data(encrypted, fernet)
    assert decrypted is not None
    assert decrypted == original_data

def test_decrypt_invalid_token():
    key = Fernet.generate_key().decode()
    fernet = get_fernet_instance(key)
    assert fernet is not None
    invalid_encrypted_data = b"gAAAAAB..." # Not a valid token for this key
    decrypted = decrypt_data(invalid_encrypted_data, fernet)
    assert decrypted is None
