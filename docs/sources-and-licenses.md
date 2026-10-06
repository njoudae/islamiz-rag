# Sources, Components, Services, and Licenses

Audited **2026-10-06**. `USED` means it runs in, or is shipped with, the product as it stands. `EVALUATION ONLY` means it was used to measure alternatives and is not part of serving answers. `OPTIONAL` means the code path exists and is off by default. No credentials belong in this file.

## Knowledge source and competition material

| Status | Item | Source | Purpose | Rights status | Notes |
|---|---|---|---|---|---|
| USED | الموسوعة الفقهية – الدرر السنية | [dorar.net/feqhia](https://dorar.net/feqhia), books of Salah and Sawm, read 2026-10-03 | The only knowledge source answers are drawn from (`OFFICIAL_HACKATHON_REFERENCE`) | Rights reserved by Dorar; no open redistribution license identified | Every answer links back to its Dorar page. See "Source text in this repository" below |
| USED | Dorar encyclopedia table of contents | [dorar.net/feqhia](https://dorar.net/feqhia), stored in `apps/site/resources/js/data/encyclopedia.json`, read 2026-10-05 | The encyclopedia page: each of the 52 books and its chapters links to its own Dorar page | Rights reserved; titles and links only, no content | Source and date are recorded in the file |
| USED | Dorar methodology pages | [method](https://dorar.net/article/1923), [accreditation description](https://dorar.net/article/1983) | Understanding the source's structure | Rights reserved; informational citation | No claim of partnership or endorsement |
| USED | Official challenge website and participant guide | [islamicaich.org](https://islamicaich.org/), [participant guide PDF](https://islamicaich.org/files/Hackathon/i2xgA3mxVhrbRe0ReLlA86kTDbFZ9QQ9eb856dq8.pdf) | Track, deliverables and judging criteria | Rights reserved; participant information use | Summarized, not redistributed |
| USED | Official scientific annex | Participant portal | Approved-source scope | Organizer material | The team confirms the exact release in the portal |

## AI models and AI services

| Status | Item | Version / access | Purpose | License / terms | Data that leaves the server |
|---|---|---|---|---|---|
| USED | BAAI/bge-m3 | Hugging Face `BAAI/bge-m3`, run locally through sentence-transformers | Embeds each index unit (once) and each question | MIT | None when run locally (the Docker setup) |
| USED | Cloudflare Workers AI, `@cf/baai/bge-m3` | Hosted API, hosted demo only (`QUERY_EMBEDDING_BACKEND=cloudflare`) | Embeds the question on a host too small to hold the model | Cloudflare service terms; model is MIT | The question text |
| USED | OpenAI API | Responses API with structured output, model set by `OPENAI_GENERATION_MODEL` | Selects the units that answer the question, writes the grounded answer, and classifies whether the question is a fiqh question | OpenAI API terms; paid service | The question, and the text of the retrieved Dorar units |
| USED | Web Speech API | The visitor's browser (Chromium-based) | Turns a spoken question into text before it is sent | Browser vendor's terms | Audio goes from the browser to the browser vendor's speech service, not to this project's servers |
| OPTIONAL | Cloudflare Workers AI, `@cf/baai/bge-reranker-base` | Hosted API, off by default (`RERANKER_PROVIDER=cloudflare`) | Reorders retrieved units | Cloudflare service terms; model is MIT | The question and the text of ten retrieved units |
| EVALUATION ONLY | intfloat/multilingual-e5-small | Hugging Face | Compared as an embedding model in the retrieval benchmark | MIT | None |
| EVALUATION ONLY | Qwen/Qwen3-Embedding-0.6B | Hugging Face | Compared as an embedding model in the retrieval benchmark | Apache-2.0 | None |
| EVALUATION ONLY | Qwen/Qwen3-Reranker-0.6B | Hugging Face | Measured as a reranker; not enabled because it did not improve the benchmark | Apache-2.0 | None |

## Software

| Status | Component | Version | Purpose | License |
|---|---|---|---|---|
| USED | Daleel project code | This repository | The product | No repository-level `LICENSE` file; see "Project license" below |
| USED | Laravel | 13.x (`apps/site/composer.lock`) | Website: pages, public API, admin area | MIT |
| USED | Inertia.js (Laravel adapter and Vue client) | 3.x | Server-driven pages | MIT |
| USED | Vue | 3.5 | Visitor pages and admin area | MIT |
| USED | Vite, laravel-vite-plugin, @vitejs/plugin-vue | Locked in `apps/site/package-lock.json` | Frontend build | MIT |
| USED | FrankenPHP (with Caddy) | `dunglas/frankenphp:1-php8.4` image | Serves the website | MIT (FrankenPHP), Apache-2.0 (Caddy) |
| USED | PHPUnit, Laravel Pint | Dev dependencies in `apps/site/composer.lock` | Website tests and formatting | BSD-3-Clause (PHPUnit), MIT (Pint) |
| USED | Lucide icons | Paths inlined in `apps/site/resources/js/lib/icons.js` | UI icons | ISC |
| USED | Inter, Tajawal, Amiri | Google Fonts, loaded by the browser | UI and quotation typefaces | SIL Open Font License 1.1 |
| USED | FastAPI | `>=0.115,<1` | AI service HTTP API | MIT |
| USED | Uvicorn | `>=0.32,<1` | ASGI server | BSD-3-Clause |
| USED | Pydantic, Pydantic Settings | `>=2.6,<3` (settings) | Data models and configuration | MIT |
| USED | sentence-transformers | `>=6.1,<7` | Loads and runs BGE-M3 | Apache-2.0 |
| USED | PyTorch | CPU build in the Docker image | Runs the embedding model | BSD-3-Clause |
| USED | NumPy | `>=2.0,<3` | Similarity search over the index | BSD-3-Clause |
| USED | OpenAI Python SDK | `>=3.22,<4` | Client for the OpenAI API | Apache-2.0 |
| USED | HTTPX | `>=0.27,<1` | Calls to Cloudflare Workers AI; source fetching during extraction | BSD-3-Clause |
| USED | psycopg | `>=3.2,<4` | PostgreSQL driver (optional conversation store, earlier ingestion path) | LGPL-3.0 |
| USED | Beautiful Soup, Typer, SQLAlchemy, python-multipart | Ranges in `apps/api/pyproject.toml` | Source parsing and the earlier ingestion tooling; installed with the service | MIT (Beautiful Soup, Typer, SQLAlchemy), Apache-2.0 (python-multipart) |
| USED | pytest, pytest-asyncio, respx | Dev ranges in `apps/api/pyproject.toml` | AI service tests | MIT (pytest), Apache-2.0 (pytest-asyncio), BSD-3-Clause (respx) |
| USED | PostgreSQL | `pgvector/pgvector:pg16` image | The website's database. The image's pgvector extension is not used | PostgreSQL License |
| USED | SQLite | Bundled with Python | Server-side conversation state for clarifications | Public domain |
| USED | Docker, Docker Compose | Host tooling | Runs the whole stack with one command | Apache-2.0 |

## Hosting and operations (hosted demo only)

| Status | Service | Purpose | Terms | Data held there |
|---|---|---|---|---|
| USED | Render (free web service) | Runs the website and the AI service in one container | Render terms of service | Application logs; conversation state in a file that is lost on restart |
| USED | Supabase (free PostgreSQL) | The website's database | Supabase terms of service | Visitor questions and answers, feedback, contact messages, the admin account |
| USED | GitHub, GitHub Actions | Source hosting; a scheduled workflow that opens the demo's home page so it does not go to sleep | GitHub terms of service | Source code only |

## First-party assets

| Status | Asset | Location | Notes |
|---|---|---|---|
| USED | Interface design and stylesheet | `apps/site/resources/css/app.css` | Designed by the team for this project |
| USED | Application screenshots | `artifacts/screenshots/official/` | Captured from the Daleel interface with prepared examples and synthetic dashboard data |
| USED | Team avatar SVGs, GitHub QR image | `assets/` | Team-provided; regenerate the QR code if the repository URL changes |

## Data and API disclosure

- **External calls when answering.** The question and the text of the retrieved units are sent to OpenAI. In the hosted demo the question is also sent to Cloudflare Workers AI for embedding. In the Docker setup the embedding runs locally and only OpenAI is called.
- **Visitor data.** Visitors are anonymous. The site stores each question, the answer state, an optional thumbs up or down, a browser-generated identifier and a keyed hash of the IP address. The contact form stores the name, email and message the visitor types.
- **No real beneficiary dataset** is used for development or evaluation. The benchmark and evaluation questions were written by the team. The dashboard history that can be seeded for demonstrations is synthetic and flagged as such.
- **No credentials** or populated `.env` file are committed.

## Source text in this repository

The extracted text of the Salah and Sawm books is committed, because the product answers from it: `artifacts/dorar_final_dataset/four_books/` and `artifacts/benchmark/final_30q_retrieval/production_index/`. Dorar's rights in that text are reserved and no redistribution license has been identified. The team has to decide, with the organizers' approved-source terms, whether these files may stay in a public repository; if not, they can be removed from it and rebuilt locally from the source pages.

## Project license

The repository has no `LICENSE` file, so no reuse rights are granted by default. Choosing a license is a decision for all contributors.
