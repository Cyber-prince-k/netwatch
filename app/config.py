from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "NetWatch Enterprise"
    environment: str = "development"
    secret_key: str = "change-me-in-production"
    database_url: str = "sqlite+aiosqlite:///./netwatch.db"
    collector_id: str = "central-collector"
    monitor_interval_seconds: int = 60

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()
