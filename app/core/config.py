from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    app_name: str = "mrhost-guest-qr-backend"
    debug: bool = False
    secret_key: str = Field("change-me", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(15, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    refresh_token_expire_days: int = Field(30, env="REFRESH_TOKEN_EXPIRE_DAYS")
    refresh_token_length: int = Field(64, env="REFRESH_TOKEN_LENGTH")
    database_url: Optional[str] = Field(None, env="DATABASE_URL")
    sqlite_url: str = Field("sqlite:///./app.db", env="SQLITE_URL")

    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    qr_token_expire_minutes: int = Field(60 * 24, env="QR_TOKEN_EXPIRE_MINUTES")

    bootstrap_admin_email: Optional[str] = Field(None, env="BOOTSTRAP_ADMIN_EMAIL")
    bootstrap_admin_password: Optional[str] = Field(None, env="BOOTSTRAP_ADMIN_PASSWORD")

    invite_expire_hours: int = Field(24, env="INVITE_EXPIRE_HOURS")
    password_reset_expire_minutes: int = Field(30, env="PASSWORD_RESET_EXPIRE_MINUTES")
    rate_limit_window_seconds: int = Field(60, env="RATE_LIMIT_WINDOW_SECONDS")
    login_rate_limit: int = Field(5, env="LOGIN_RATE_LIMIT")
    reset_rate_limit: int = Field(5, env="RESET_RATE_LIMIT")
    totp_issuer: str = Field("MrHost Admin", env="TOTP_ISSUER")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
