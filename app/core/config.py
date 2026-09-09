from functools import lru_cache

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_env: str = "local"

    database_url: str | None = None
    postgres_connection_string: str | None = None

    events_provider_base_url: str = ""
    events_provider_api_key: str = ""

    sync_interval_seconds: int = 86400
    seats_cache_ttl_seconds: int = 30

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @model_validator(mode="after")
    def configure_database_url(self) -> "Settings":
        database_url = self.database_url or self.postgres_connection_string

        if not database_url:
            raise ValueError(
                "DATABASE_URL or POSTGRES_CONNECTION_STRING must be configured"
            )

        if database_url.startswith("postgres://"):
            database_url = database_url.replace(
                "postgres://",
                "postgresql+asyncpg://",
                1,
            )
        elif database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://",
                "postgresql+asyncpg://",
                1,
            )

        self.database_url = database_url
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
