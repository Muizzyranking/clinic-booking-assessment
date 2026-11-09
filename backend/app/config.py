from functools import lru_cache
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        frozen=True,
    )

    api_key: str = Field(min_length=1)
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    rate_limit_max_attempts: int = 5
    rate_limit_window_seconds: int = 60
    default_page_size: int = 20
    max_page_size: int = 100

    seed_on_startup: bool = True
    seed_random_seed: int | None = None

    cors_origins: str = "*"

    @field_validator("api_key", mode="before")
    @classmethod
    def strip_api_key(cls, value: object) -> object:
        return value.strip() if isinstance(value, str) else value

    @field_validator("log_level", mode="before")
    @classmethod
    def upper_log_level(cls, value: object) -> object:
        return value.upper() if isinstance(value, str) else value

    @property
    def cors_origin_list(self) -> list[str]:
        return [item.strip() for item in self.cors_origins.split(",") if item.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
