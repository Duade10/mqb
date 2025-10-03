from __future__ import annotations

import base64
import hmac
import secrets
import time
from hashlib import sha1
from typing import Optional
from urllib.parse import quote

from app.core.config import get_settings


settings = get_settings()


def _base32_decode(secret: str) -> bytes:
    padding = "=" * ((8 - len(secret) % 8) % 8)
    return base64.b32decode(secret.upper() + padding)


def _hotp(key: bytes, counter: int, digits: int = 6) -> str:
    counter_bytes = counter.to_bytes(8, "big")
    hmac_digest = hmac.new(key, counter_bytes, sha1).digest()
    offset = hmac_digest[-1] & 0x0F
    code = (int.from_bytes(hmac_digest[offset : offset + 4], "big") & 0x7FFFFFFF) % (10**digits)
    return str(code).zfill(digits)


def _totp_now(secret: str, timestamp: Optional[float] = None, interval: int = 30) -> str:
    key = _base32_decode(secret)
    current_time = int((timestamp or time.time()) // interval)
    return _hotp(key, current_time)


def generate_totp_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode("utf-8").rstrip("=")


def build_totp_uri(secret: str, email: str) -> str:
    issuer = quote(settings.totp_issuer)
    label = quote(f"{settings.totp_issuer}:{email}")
    return f"otpauth://totp/{label}?secret={secret}&issuer={issuer}&period=30"


def verify_totp(secret: str, code: str) -> bool:
    if not secret or not code:
        return False
    code = code.strip()
    try:
        for offset in (-1, 0, 1):
            comparison = _totp_now(secret, timestamp=time.time() + offset * 30)
            if comparison == code.zfill(6):
                return True
    except (ValueError, TypeError, base64.binascii.Error):
        return False
    return False


def generate_recovery_codes(count: int = 10) -> list[str]:
    return [secrets.token_hex(4) + secrets.token_hex(4) for _ in range(count)]

