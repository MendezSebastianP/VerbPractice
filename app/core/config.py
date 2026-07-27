from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_env: str = Field(default="development", alias="APP_ENV")
    app_name: str = Field(default="VerbPractice", alias="APP_NAME")
    app_base_url: str = Field(default="http://127.0.0.1:8000", alias="APP_BASE_URL")
    secret_key: str = Field(default="change-me", alias="SECRET_KEY")
    database_url: str = Field(
        default="postgresql+asyncpg://postgres:postgres@localhost:5432/verbpractice",
        alias="DATABASE_URL",
    )
    database_use_null_pool: bool = Field(default=True, alias="DATABASE_USE_NULL_POOL")
    openai_api_key: str | None = Field(default=None, alias="OPENAI_API_KEY")
    offline_sense_model_enabled: bool = Field(
        default=True, alias="OFFLINE_SENSE_MODEL_ENABLED"
    )
    offline_sense_model_dir: str = Field(
        default=".local/models/multilingual-e5-small",
        alias="OFFLINE_SENSE_MODEL_DIR",
    )
    offline_nli_model_enabled: bool = Field(
        default=True, alias="OFFLINE_NLI_MODEL_ENABLED"
    )
    offline_nli_model_dir: str = Field(
        default=".local/models/multilingual-nli",
        alias="OFFLINE_NLI_MODEL_DIR",
    )
    default_theme: str = Field(default="arcade", alias="DEFAULT_THEME")
    rate_limit_per_minute: int = Field(default=80, alias="RATE_LIMIT_PER_MINUTE")
    log_level: str = Field(default="INFO", alias="LOG_LEVEL")
    request_id_header: str = Field(default="X-Request-ID", alias="REQUEST_ID_HEADER")


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
