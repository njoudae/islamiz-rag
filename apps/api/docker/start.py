"""Container entrypoint for the Daleel AI service.

Makes a fresh `docker compose up` self-sufficient:
  1. check that the committed production index and prompts are in the image,
  2. make sure the embedding model named by the index is in the model cache,
  3. hand over to uvicorn.
"""
from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from app.config import get_settings

ROOT = Path(__file__).resolve().parents[3]


def log(message: str) -> None:
    print(f"[daleel-ai] {message}", flush=True)


def main() -> None:
    settings = get_settings()
    index_dir = Path(settings.final_index_dir)
    required = [index_dir / name for name in ("manifest.json", "units.jsonl", "unit_ids.json", "embeddings.npy")]
    required += [ROOT / "prompts" / name for name in ("selector_prompt.txt", "generation_prompt.txt")]
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise SystemExit(f"missing files the answer pipeline needs: {', '.join(missing)}")

    manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
    log(f"production index: {manifest['unit_count']} units embedded with {manifest['model_name']}")

    # Load the model once the same way the pipeline does, so exactly the files it needs are in the
    # cache before the API accepts questions. Without this the first visitor waits for the download.
    from sentence_transformers import SentenceTransformer

    try:
        SentenceTransformer(manifest["model_name"], device="cpu", trust_remote_code=True, local_files_only=True)
        log(f"model weights already cached: {manifest['model_name']}")
    except Exception:
        log(f"downloading model weights: {manifest['model_name']} (first run only, about 2.3 GB)")
        SentenceTransformer(manifest["model_name"], device="cpu", trust_remote_code=True)
        log("model weights downloaded")

    Path(settings.conversation_db_path).parent.mkdir(parents=True, exist_ok=True)

    host = os.environ.get("HOST", "0.0.0.0")
    port = os.environ.get("PORT", "8000")
    log(f"starting API on {host}:{port}")
    os.execvp(
        sys.executable,
        [sys.executable, "-m", "uvicorn", "app.main:app", "--app-dir", str(ROOT / "apps" / "api"), "--host", host, "--port", port],
    )


if __name__ == "__main__":
    main()
