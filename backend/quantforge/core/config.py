from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Runtime settings loaded from environment variables."""

    model_config = SettingsConfigDict(env_file=".env", env_prefix="QUANTFORGE_", extra="ignore")

    environment: str = "development"
    database_url: str = Field(default="postgresql://quantforge:quantforge@localhost:5432/quantforge")
    redis_url: str = Field(default="redis://localhost:6379/0")
    parquet_cache_dir: str = Field(default="./var/parquet")

    oanda_api_url: str = Field(default="https://api-fxpractice.oanda.com/v3")
    oanda_account_id: str | None = None
    oanda_api_token: str | None = None


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

