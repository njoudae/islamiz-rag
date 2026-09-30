# Daleel Runbook

The text path is real: PostgreSQL/pgvector → multilingual E5 → lexical/vector fusion → Qwen reranking → evidence gate → OpenAI generation → citation validation. Voice remains mock/experimental.

## Prerequisites

- Python 3.11+
- Node.js 20+ and npm
- Docker with Compose
- An OpenAI API key
- Sufficient RAM for `intfloat/multilingual-e5-small` and `Qwen/Qwen3-Reranker-0.6B` on CPU

## Environment

From the repository root:

```powershell
Copy-Item .env.example .env
```

Set a local `POSTGRES_PASSWORD`, place the same value in `DATABASE_URL`, and set `OPENAI_API_KEY`. Never commit or print `.env`.

## Install

```powershell
python -m venv apps/api/.venv-real
apps/api/.venv-real/Scripts/python -m pip install -e ".\apps\api[dev]"
npm ci
```

On macOS/Linux use `apps/api/.venv-real/bin/python` instead.

## PostgreSQL and schema

```powershell
docker compose up -d postgres
docker compose ps
```

On first initialization, `infra/schema.sql` enables pgvector and creates the tables/indexes. If the volume already existed before a schema change, apply the SQL explicitly or create a clean local volume only when you intentionally want to discard local data.

## Knowledge-base preparation

The repository contains the controlled 40-document normalized artifact in `artifacts/corpus/documents.jsonl`. Build chunks, real E5 embeddings, the manifest, and load PostgreSQL:

```powershell
Push-Location apps/api
.\.venv-real\Scripts\python -m app.ingestion.cli build-real-index
Pop-Location
```

This creates `artifacts/chunks/chunks.jsonl`, `artifacts/embeddings/manifest.json`, and a local ignored `chunk_embeddings.npy`, then loads 40 documents, 88 chunks, and 88 vectors. To reload an already-generated local matrix without rerunning E5:

```powershell
Push-Location apps/api
.\.venv-real\Scripts\python -m app.ingestion.cli load-cached-index
Pop-Location
```

Do not recrawl unless authorized and necessary. Source redistribution rights remain a publication blocker; see `docs/sources-and-licenses.md`.

## Backend

```powershell
apps/api/.venv-real/Scripts/python -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

Health: `http://127.0.0.1:8000/health`. API docs: `http://127.0.0.1:8000/docs`.

The first question loads E5 and Qwen and may take noticeably longer on CPU.

## Frontend

In another terminal:

```powershell
npm run dev
```

Open `http://localhost:3000`.

## Verification and evaluation

```powershell
# Unit and safety tests (not real RAG accuracy)
apps/api/.venv-real/Scripts/python -m pytest apps/api/tests

# Deterministic offline behavior suite using mocks
apps/api/.venv-real/Scripts/python evaluate.py

# Real PostgreSQL + E5 + lexical/hybrid retrieval evaluation
$env:PYTHONPATH="apps/api"
apps/api/.venv-real/Scripts/python evaluate_real_rag.py

# Real Qwen reranking over persisted Top-20 retrieval candidates
apps/api/.venv-real/Scripts/python rerank_real_rag.py

# Frontend production build
npm run build

# Public-repository audit
apps/api/.venv-real/Scripts/python scripts/repository_audit.py
```

Real outputs are under `artifacts/retrieval/`, `artifacts/reranking/`, `artifacts/generation/`, and `artifacts/evaluation/`. `evaluation/results.json` and `evaluation/REPORT.md` belong to the separate deterministic safety suite.

## Shutdown

Stop the API and frontend with `Ctrl+C`, then:

```powershell
docker compose down
```

Do not add `-v` unless you intentionally want to delete the database volume.
