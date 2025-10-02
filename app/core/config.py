from functools import lru_cache
from typing import Optional

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    app_name: str = "mrhost-guest-qr-backend"
    debug: bool = False
    secret_key: str = Field("change-me", env="SECRET_KEY")
    access_token_expire_minutes: int = Field(60, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    database_url: Optional[str] = Field(None, env="DATABASE_URL")
    sqlite_url: str = Field("sqlite:///./app.db", env="SQLITE_URL")

    jwt_algorithm: str = Field("HS256", env="JWT_ALGORITHM")
    qr_token_expire_minutes: int = Field(60 * 24, env="QR_TOKEN_EXPIRE_MINUTES")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
