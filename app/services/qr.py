from datetime import datetime, timedelta
from typing import Any, Dict

import jwt

from app.core.config import get_settings


settings = get_settings()


def create_qr_token(listing_id: int) -> str:
    payload: Dict[str, Any] = {
        "listing_id": listing_id,
        "exp": datetime.utcnow() + timedelta(minutes=settings.qr_token_expire_minutes),
        "type": "listing_qr",
    }
    return jwt.encode(payload, settings.secret_key, algorithm=settings.jwt_algorithm)


def decode_qr_token(token: str) -> Dict[str, Any]:
    data = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
    if data.get("type") != "listing_qr":
        raise jwt.InvalidTokenError("Invalid token type")
    return data
