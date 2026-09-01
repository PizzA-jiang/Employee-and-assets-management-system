"""Fernet symmetric encryption service for API keys and secrets."""
import os
import logging
from base64 import urlsafe_b64encode, urlsafe_b64decode
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

logger = logging.getLogger(__name__)

_ENCRYPTION_KEY_ENV = "ENCRYPTION_KEY"
_fernet_instance = None


def _get_or_create_key() -> bytes:
    key_str = os.getenv(_ENCRYPTION_KEY_ENV)
    if key_str:
        return urlsafe_b64decode(key_str.encode())
    master = os.getenv("SECRET_KEY", "default-master-key-change-in-production")
    salt = b"asset-management-ai-config-salt"
    kdf = PBKDF2HMAC(algorithm=hashes.SHA256(), length=32, salt=salt, iterations=100_000)
    return kdf.derive(master.encode())


def _get_fernet() -> Fernet:
    global _fernet_instance
    if _fernet_instance is None:
        _fernet_instance = Fernet(urlsafe_b64encode(_get_or_create_key()))
    return _fernet_instance


def encrypt(plain_text: str) -> str:
    if not plain_text:
        return ""
    try:
        return _get_fernet().encrypt(plain_text.encode()).decode()
    except Exception:
        logger.exception("Encryption failed")
        raise


def decrypt(cipher_text: str) -> str:
    if not cipher_text:
        return ""
    try:
        return _get_fernet().decrypt(cipher_text.encode()).decode()
    except Exception:
        logger.exception("Decryption failed")
        raise


def mask_value(value: str) -> str:
    if not value:
        return ""
    if len(value) <= 8:
        return "*" * len(value)
    return value[:4] + "*" * (len(value) - 8) + value[-4:]
