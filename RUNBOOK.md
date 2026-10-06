# Daleel Runbook

The text path is real: BGE-M3 dense retrieval over the committed production index (584 units, Salah and Sawm) → Top-5 → grounded source selection → OpenAI generation → server-side citation and evidence validation. Voice questions are transcribed in the visitor's browser and then follow the same text path; the AI service's own speech endpoints remain mock.

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

1. PostgreSQL starts; the website keeps its data there.
2. The `ai` container already holds the production index and the prompts. It downloads the embedding model `BAAI/bge-m3`, about 2.3 GB, into a Docker volume. Wait for `[daleel-ai] starting API` in the logs. Until then the site answers questions with a "service unavailable" screen.
3. The `site` container creates its own `site` schema, runs migrations, and seeds the admin account. With `SEED_DEMO_DATA=true` it also adds about 90 days of synthetic questions, flagged as demo and labelled in the admin area, so the dashboards are not empty. Remove them with `docker compose exec site php artisan daleel:demo-data --purge`.
4. The first question loads the embedding model into memory and is noticeably slower than later ones.

Later starts skip the download and the seeding and take seconds. If a port is already in use, change `SITE_PORT`, `AI_PORT` or `POSTGRES_PORT` in `.env` and rebuild.

```powershell
docker compose logs -f ai       # follow the AI service
docker compose down             # stop; add -v only to delete the database, conversations and model cache
```

### Services

| Service | Stack | Role |
|---|---|---|
| `site` | Laravel 13, Inertia, Vue 3, FrankenPHP | Visitor pages, public API, question log, admin area. |
| `ai` | FastAPI, BGE-M3, OpenAI | The RAG pipeline, answering from the file index. Conversation state in SQLite on a volume. Not reachable from browsers. |
| `postgres` | PostgreSQL 16 | The website's data, in schema `site`. The AI service does not use it. |

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
- An OpenAI API key
- Sufficient RAM for `BAAI/bge-m3` on CPU

## Environment

From the repository root:

```powershell
Copy-Item .env.example .env
```

Set `OPENAI_API_KEY`. Never commit or print `.env`.

## Install

```powershell
python -m venv apps/api/.venv-real
apps/api/.venv-real/Scripts/python -m pip install -e ".\apps\api[dev]"
```

On macOS/Linux use `apps/api/.venv-real/bin/python` instead.

The service loads the embedding model offline, so download it once:

```powershell
apps/api/.venv-real/Scripts/hf download BAAI/bge-m3
```

## Backend

```powershell
apps/api/.venv-real/Scripts/python -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

Health: `http://127.0.0.1:8000/health`. API docs: `http://127.0.0.1:8000/docs`.

The first question loads BGE-M3 and may take noticeably longer on CPU.

## Verification and evaluation

```powershell
# AI service tests: the answer pipeline and the routes. No key, model or network needed.
apps/api/.venv-real/Scripts/python -m pytest apps/api/tests

# Final generation evaluation: 10 cases against the real pipeline (uses the OpenAI key)
$env:PYTHONPATH="apps/api"
apps/api/.venv-real/Scripts/python scripts/run_generation_final_test_10.py

# Retrieval benchmark and index rebuild (needs a GPU and three embedding models)
python run_final_30q_pipeline.py

# Website tests (see "Tests" above)

# Public-repository audit: secrets, broken documentation links, required files
apps/api/.venv-real/Scripts/python scripts/repository_audit.py
```

Saved results of the last runs are in `evaluation/generation_final_report.md` and `artifacts/benchmark/final_30q_retrieval/FINAL_BENCHMARK.md`.

Four tests in the suite are marked as expected failures: they exercise the earlier experimental pipeline code, which no longer serves answers.

## Shutdown

Stop the API with `Ctrl+C`, then:

```powershell
docker compose down
```

Do not add `-v` unless you intentionally want to delete the database volume.
