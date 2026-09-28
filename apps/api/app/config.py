from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Daleel API"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://daleel@localhost:5432/daleel"
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    crawl_delay_seconds: float = 2.5
    crawl_user_agent: str = "DaleelResearchBot/0.1 (+configure-contact)"
    stt_provider: str = "mock"
    tts_provider_ar: str = "mock"
    tts_provider_en: str = "mock"
    embedding_provider: str = "mock"
    reranker_provider: str = "mock"
    generation_provider: str = "mock"
    default_source_collection: str = "OFFICIAL_HACKATHON_REFERENCE"


@lru_cache
def get_settings() -> Settings:
    return Settings()
