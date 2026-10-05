"""Container entrypoint for the Daleel AI service.

Makes a fresh `docker compose up` self-sufficient:
  1. wait for PostgreSQL,
  2. apply the idempotent knowledge-base schema,
  3. build the E5 index from the committed corpus when the database is empty,
  4. make sure the reranker weights are in the model cache,
  5. hand over to uvicorn.
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from pathlib import Path

import psycopg

from app.config import get_settings
from app.repositories.postgres import psycopg_url

ROOT = Path(__file__).resolve().parents[3]
SCHEMA = ROOT / "infra" / "schema.sql"
DOCUMENTS = ROOT / "artifacts" / "corpus" / "documents.jsonl"
ARTIFACTS = ROOT / "artifacts"


def log(message: str) -> None:
    print(f"[daleel-ai] {message}", flush=True)


def wait_for_database(url: str, attempts: int = 60, delay: float = 2.0) -> None:
    for attempt in range(1, attempts + 1):
        try:
            with psycopg.connect(url, connect_timeout=5):
                return
        except psycopg.OperationalError as error:
            log(f"waiting for PostgreSQL ({attempt}/{attempts}): {str(error).strip().splitlines()[0]}")
            time.sleep(delay)
    raise SystemExit("PostgreSQL did not become reachable")


def apply_schema(url: str) -> None:
    with psycopg.connect(url) as connection:
        connection.execute(SCHEMA.read_text(encoding="utf-8"))
        connection.commit()


def embedding_count(url: str) -> int:
    with psycopg.connect(url) as connection:
        return connection.execute("SELECT count(*) FROM embeddings").fetchone()[0]


def main() -> None:
    settings = get_settings()
    url = psycopg_url(settings.database_url)

    wait_for_database(url)
    apply_schema(url)

    if embedding_count(url) == 0:
        log(f"knowledge base is empty; building the index with {settings.e5_model} (first run only)")
        from app.ingestion.database import build_real_index
        from app.providers.real import E5EmbeddingProvider

        manifest = asyncio.run(
            build_real_index(DOCUMENTS, ARTIFACTS, settings.database_url, E5EmbeddingProvider(settings.e5_model), settings.e5_model)
        )
        log(f"indexed {manifest['document_count']} documents / {manifest['chunk_count']} chunks")
    else:
        log(f"knowledge base already holds {embedding_count(url)} embeddings; skipping the index build")

    from huggingface_hub import snapshot_download

    for model in (settings.e5_model, settings.qwen_reranker_model):
        log(f"ensuring model weights are cached: {model}")
        snapshot_download(model)

    host = os.environ.get("HOST", "0.0.0.0")
    port = os.environ.get("PORT", "8000")
    log(f"starting API on {host}:{port}")
    os.execvp(
        sys.executable,
        [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", str(ROOT / "apps" / "api"), "--host", host, "--port", port],
    )


if __name__ == "__main__":
    main()
