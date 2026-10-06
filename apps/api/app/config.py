from functools import lru_cache
from pathlib import Path
from pydantic import SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", str(Path(__file__).resolve().parents[3] / ".env")),
        extra="ignore",
    )

    app_name: str = "Daleel API"
    app_env: str = "development"
    database_url: str = "postgresql+psycopg://daleel@localhost:5432/daleel"
    allowed_origins: list[str] = ["http://localhost:3000", "http://127.0.0.1:3000"]
    crawl_delay_seconds: float = 2.5
    crawl_user_agent: str = "DaleelResearchBot/0.1 (+configure-contact)"
    stt_provider: str = "disabled"
    tts_provider_ar: str = "disabled"
    tts_provider_en: str = "disabled"
    embedding_provider: str = "bge_m3"
    reranker_provider: str = "disabled"
    generation_provider: str = "openai"
    e5_model: str = "intfloat/multilingual-e5-small"
    qwen_reranker_model: str = "Qwen/Qwen3-Reranker-0.6B"
    openai_generation_model: str = "gpt-6.1-sol"
    openai_api_key: SecretStr | None = None
    # Shared secret the website backend sends as X-Internal-Token. Unset = open (local dev).
    internal_api_token: SecretStr | None = None
    default_source_collection: str = "OFFICIAL_HACKATHON_REFERENCE"
    final_index_dir: str = str(
        Path(__file__).resolve().parents[3]
        / "artifacts"
        / "benchmark"
        / "final_30q_retrieval"
        / "production_index"
    )
    conversation_db_path: str = str(
        Path(__file__).resolve().parents[3] / "data" / "conversations.sqlite3"
    )
    retrieval_device: str | None = None
    # Where the question is embedded: "local" loads the model in this process;
    # "cloudflare" calls the same model on Cloudflare Workers AI (for small hosts).
    query_embedding_backend: str = "local"
    # RERANKER_PROVIDER=cloudflare reorders the best RERANK_DEPTH units with the hosted reranker
    # before the top five go to the selector. Any other value leaves retrieval as it is.
    rerank_depth: int = 10
    cloudflare_account_id: str | None = None
    cloudflare_api_token: SecretStr | None = None

    @field_validator("final_index_dir", "conversation_db_path")
    @classmethod
    def relative_to_repository_root(cls, value: str) -> str:
        """A relative path, as in .env.example, means relative to the repository, wherever the process starts."""
        path = Path(value)
        return str(path if path.is_absolute() else Path(__file__).resolve().parents[3] / path)


@lru_cache
def get_settings() -> Settings:
    return Settings()
