# Daleel Runbook

The text path is real: PostgreSQL/pgvector → multilingual E5 → lexical/vector fusion → Qwen reranking → evidence gate → OpenAI generation → citation validation. Voice questions are transcribed in the visitor's browser and then follow the same text path; the AI service's own speech endpoints remain mock.

## Quick start (Docker, recommended)

Requirements: Docker Desktop (or Docker Engine with Compose v2) and an OpenAI API key. Nothing else needs to be installed.

```powershell
Copy-Item .env.example .env     # macOS/Linux: cp .env.example .env
# edit .env and set OPENAI_API_KEY
docker compose up --build
```

| What | URL |
|---|---|
| Visitor site | `http://localhost:8080` (contact form at `/contact`) |
| Admin area | `http://localhost:8080/login`, or the "دخول المشرفين" button |
| AI service health and API docs | `http://127.0.0.1:8000/health`, `http://127.0.0.1:8000/docs` |

Admin login (dummy account, set by `ADMIN_EMAIL` / `ADMIN_PASSWORD` in `.env`; the login page also shows it with a fill button):

```text
admin@daleel.sa
daleel-admin-2026
```

What happens on the first start, without any manual step:

1. PostgreSQL starts with pgvector and the knowledge-base schema.
2. The `ai` container builds the E5 index from `artifacts/corpus/documents.jsonl` (40 documents, 88 chunks) and downloads the E5 and Qwen models, about 1.7 GB, into a Docker volume. Wait for `[daleel-ai] starting API` in the logs. Until then the site answers questions with a "service unavailable" screen.
3. The `site` container creates its own `site` schema, runs migrations, and seeds the admin account. With `SEED_DEMO_DATA=true` it also adds about 90 days of synthetic questions, flagged as demo and labelled in the admin area, so the dashboards are not empty. Remove them with `docker compose exec site php artisan daleel:demo-data --purge`.
4. The first question loads both models into memory and is noticeably slower than later ones.

Later starts skip steps 2 and 3 and take seconds. If a port is already in use, change `SITE_PORT`, `AI_PORT` or `POSTGRES_PORT` in `.env` and rebuild.

```powershell
docker compose logs -f ai       # follow the AI service
docker compose down             # stop; add -v only to delete the database and model cache
```

### Services

| Service | Stack | Role |
|---|---|---|
| `site` | Laravel 13, Inertia, Vue 3, FrankenPHP | Visitor pages, public API, question log, admin area. |
| `ai` | FastAPI, E5, Qwen reranker, OpenAI | The RAG pipeline. Not reachable from browsers. |
| `postgres` | PostgreSQL 16 + pgvector | Schema `public` for the knowledge base, schema `site` for the website. |

### Tests

```powershell
# Website (Laravel): pages, API proxy, feedback, question log, review queue, dashboards
docker build --target base -t daleel-site-dev apps/site
docker run --rm -v "${PWD}/apps/site:/app" daleel-site-dev sh -c "composer install --no-interaction && php artisan test"
```

The Python suites are listed under "Verification and evaluation" below.

## Manual setup of the AI service (without Docker)

The rest of this document runs the AI service directly on the host, for AI development and evaluation. It bypasses the website, so nothing is logged to the admin area. Ask questions through `http://127.0.0.1:8000/docs`, or point a Docker-run website at the host service by setting `AI_SERVICE_URL=http://host.docker.internal:8000` for the `site` service.

## Prerequisites

- Python 3.11+
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

# Website tests (see "Tests" above)

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
