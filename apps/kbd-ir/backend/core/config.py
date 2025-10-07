"""Application configuration management."""
from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import BaseSettings, Field


class Settings(BaseSettings):
    """Runtime configuration loaded from environment variables."""

    app_name: str = "KBD-IR API"
    environment: Literal["prod", "stg", "dev", "local"] = Field(
        default="prod", env="KBDIR_ENVIRONMENT"
    )
    debug: bool = Field(default=False, env="KBDIR_DEBUG")

    database_url: str = Field(
        default="sqlite:///" + str((Path(__file__).resolve().parent.parent / "data" / "kbd_ir.db")),
        env="KBDIR_DATABASE_URL",
    )

    secret_key: str = Field(default="change-me", env="KBDIR_SECRET_KEY")
    access_token_expire_minutes: int = Field(default=60 * 12, env="KBDIR_ACCESS_TOKEN_EXPIRE_MINUTES")

    aws_region: str = Field(default="ap-northeast-1", env="AWS_REGION")
    s3_bucket: str = Field(default="kbdir-prod", env="KBDIR_S3_BUCKET")
    s3_base_prefix: str = Field(default="kbdir/tournaments", env="KBDIR_S3_BASE_PREFIX")

    ses_sender: str = Field(default="kbdir@maru65536.com", env="KBDIR_SES_SENDER")
    password_reset_expiration_minutes: int = Field(default=30, env="KBDIR_PASSWORD_RESET_EXPIRATION_MINUTES")

    cors_allow_origins: str = Field(default="*", env="KBDIR_CORS_ALLOW_ORIGINS")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    """Return a cached Settings instance."""

    return Settings()


settings = get_settings()
