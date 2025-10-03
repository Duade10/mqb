from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, validator


def _normalize_email(value: str) -> str:
    if not isinstance(value, str) or "@" not in value:
        raise ValueError("Invalid email address")
    local, _, domain = value.partition("@")
    if not local or not domain:
        raise ValueError("Invalid email address")
    return value.strip().lower()


class TokenPair(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int = Field(..., description="Access token expiry in seconds")


class TokenPayload(BaseModel):
    sub: str
    role: str
    pwd: str


class LoginRequest(BaseModel):
    email: str
    password: str
    totp_code: Optional[str] = None
    recovery_code: Optional[str] = None

    _validate_email = validator("email", allow_reuse=True)(_normalize_email)


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str


class BootstrapResponse(BaseModel):
    email: str

    _validate_email = validator("email", allow_reuse=True)(_normalize_email)


class InviteCreateRequest(BaseModel):
    email: str
    expires_in_hours: Optional[int] = None

    _validate_email = validator("email", allow_reuse=True)(_normalize_email)


class InviteResponse(BaseModel):
    code: str
    expires_at: datetime


class RegisterRequest(BaseModel):
    email: str
    password: str
    invite_code: str

    _validate_email = validator("email", allow_reuse=True)(_normalize_email)


class PasswordResetRequest(BaseModel):
    email: str

    _validate_email = validator("email", allow_reuse=True)(_normalize_email)


class PasswordResetSubmit(BaseModel):
    token: str
    password: str


class TOTPSetupResponse(BaseModel):
    secret: str
    uri: str


class TOTPEnableRequest(BaseModel):
    totp_code: str


class TOTPDisableRequest(BaseModel):
    totp_code: Optional[str] = None
    recovery_code: Optional[str] = None


class AdminProfile(BaseModel):
    id: int
    email: str
    role: str
    is_active: bool
    totp_enabled: bool
    created_at: datetime
    updated_at: datetime

    _validate_email = validator("email", allow_reuse=True)(_normalize_email)

    class Config:
        orm_mode = True


class AdminUpdateRequest(BaseModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
