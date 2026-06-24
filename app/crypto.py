
#/ =====================================================================================
#/  AES-256-GCM encryption for personal data (PII)
#/  EncryptedString — SQLAlchemy TypeDecorator for transparent column encryption
#/ =====================================================================================

import os
import base64
import config
from typing import Optional
from sqlalchemy import TypeDecorator, Text
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

#* ─── Key loading ───
#! DATA_ENCRYPTION_KEY must be a 256-bit key encoded in base64
#! Generate: python -c "import base64,os; print(base64.b64encode(os.urandom(32)).decode())"
def _load_key() -> bytes:
    raw = config.DATA_ENCRYPTION_KEY
    if not raw:
        raise RuntimeError(
            "DATA_ENCRYPTION_KEY is not set. Generate one with:\n"
            "  python -c \"import base64,os; print(base64.b64encode(os.urandom(32)).decode())\""
        )
    try:
        return base64.b64decode(raw)
    except Exception as e:
        raise RuntimeError(f"Invalid DATA_ENCRYPTION_KEY (must be base64-encoded 32 bytes): {e}")

_KEY: Optional[bytes] = None

def get_key() -> bytes:
    global _KEY
    if _KEY is None:
        _KEY = _load_key()
    return _KEY


#* ─── Encrypt / Decrypt helpers ───
def encrypt_value(plaintext: str) -> str:
    if not plaintext:
        return plaintext
    key = get_key()
    aesgcm = AESGCM(key)
    nonce = os.urandom(12)
    ct = aesgcm.encrypt(nonce, plaintext.encode("utf-8"), None)
    return base64.b64encode(nonce + ct).decode("utf-8")


def decrypt_value(ciphertext: str) -> str:
    if not ciphertext:
        return ciphertext
    key = get_key()
    data = base64.b64decode(ciphertext)
    nonce = data[:12]
    ct = data[12:]
    aesgcm = AESGCM(key)
    return aesgcm.decrypt(nonce, ct, None).decode("utf-8")


#* ─── SQLAlchemy TypeDecorator — transparent string encryption ───
class EncryptedStr(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            return encrypt_value(value)
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return decrypt_value(value)
        return value


#* ─── SQLAlchemy TypeDecorator — transparent date encryption (stored as ISO text) ───
from datetime import date

class EncryptedDate(TypeDecorator):
    impl = Text
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is not None:
            if isinstance(value, date):
                return encrypt_value(value.isoformat())
            return encrypt_value(str(value))
        return value

    def process_result_value(self, value, dialect):
        if value is not None:
            return date.fromisoformat(decrypt_value(value))
        return value
