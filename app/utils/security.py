import base64
import secrets
import string
from datetime import datetime, timedelta
from hashlib import pbkdf2_hmac, sha256
from typing import Any, Dict

import jwt

from app.core.config import get_settings


settings = get_settings()


def create_access_token(data: Dict[str, Any], expires_delta: timedelta | None = None) -> str:
    to_encode = data.copy()
    expire = datetime.utcnow() + (
        expires_delta or timedelta(minutes=settings.access_token_expire_minutes)
    )
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, settings.secret_key, algorithm=settings.jwt_algorithm)
    return encoded_jwt


def verify_password(plain_password: str, hashed_password: str) -> bool:
    decoded = base64.b64decode(hashed_password.encode("utf-8"))
    salt = decoded[:16]
    stored_hash = decoded[16:]
    new_hash = pbkdf2_hmac("sha256", plain_password.encode("utf-8"), salt, 120000)
    return secrets.compare_digest(new_hash, stored_hash)


def get_password_hash(password: str) -> str:
    salt = secrets.token_bytes(16)
    hashed = pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120000)
    return base64.b64encode(salt + hashed).decode("utf-8")


def hash_token(token: str) -> str:
    return sha256(token.encode("utf-8")).hexdigest()


def generate_refresh_token(length: int | None = None) -> str:
    alphabet = string.ascii_letters + string.digits
    token_length = length or settings.refresh_token_length
    return "".join(secrets.choice(alphabet) for _ in range(token_length))


def password_meets_policy(password: str) -> bool:
    if len(password) < 12:
        return False
    has_upper = any(c.isupper() for c in password)
    has_lower = any(c.islower() for c in password)
    has_digit = any(c.isdigit() for c in password)
    has_symbol = any(c in string.punctuation for c in password)
    return has_upper and has_lower and has_digit and has_symbol
