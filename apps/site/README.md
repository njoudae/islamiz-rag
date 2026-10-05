# Daleel website

Laravel 13 + Inertia + Vue 3 application: the visitor pages, the admin area, and everything between the browser and the AI service. It owns all ordinary web application work, so the AI service (`apps/api`) can stay a stateless pipeline. The UI follows the approved design (`fatwa-standalone.html`), with the Daleel name and the design's logo; its stylesheet is `resources/css/app.css`.

```text
browser ──> site (this app) ──> ai (FastAPI, internal) ──> postgres
              │
              └── postgres, schema "site": questions, admin user, sessions
```

## What it does

| Area | Route | Notes |
|---|---|---|
| Home | `GET /` | Hero ask bar, the seven outcomes, the encyclopedia's book groups. |
| Ask | `GET /ask` (`/try` redirects) | Chat with text or voice (browser speech-to-text) and feedback. A blocked or missing microphone shows an alert instead of recording. Accepts `?q=`, `?voice=1`, `?prefill=`. |
| Encyclopedia | `GET /encyclopedia` | The 52 books with their entry counts and chapters, searchable by book or chapter. Every book and chapter links to its own Dorar page. Accepts `?group=`. |
| Contact | `GET /contact`, `POST /contact` | Name, email, topic, optional pasted question, message (1,500 characters), optional emailed copy, and an FAQ. Rate-limited, with a honeypot field against bots. |
| Ask | `POST /api/v1/ask` | No login. Validates, rate-limits, forwards to the AI service, stores the question with its state and channel. `parent_id` continues a clarification. |
| Feedback | `POST /api/v1/questions/{id}/feedback` | Thumbs up or down plus a reason. Only the browser that asked (same `X-Visitor-Id`) may rate. |
| Status | `GET /api/v1/status` | Whether live answers are available; the ask page switches to demo mode when not. |
| Admin login | `GET /login` | Single seeded administrator. Visitors never log in. |
| Overview | `GET /admin` | KPIs with change against the previous period, outcome table, daily trend, latest questions. `?period=7|30|90`. |
| Review queue | `GET /admin/review`, `POST /admin/review/{id}` | Filter, search, open a question, save a verdict and the correct state. |
| Knowledge gaps | `GET /admin/gaps`, `POST /admin/gaps/tasks`, `PATCH /admin/gaps/tasks/{id}` | Unanswered questions grouped by the nearest indexed section, repeated off-topic questions, follow-up tasks, and coverage per section. |
| Model quality | `GET /admin/quality`, `GET /admin/quality/export` | Confusion matrix, citation accuracy and transcription error from reviews; one column per generation model seen in the log; failure causes; feedback reasons; evaluation-set download. |
| Contact inbox | `GET /admin/messages`, `PATCH /admin/messages/{id}` | New, read and archived messages; opening a message marks it read. |
| Health | `GET /up` | Used by the container health check. |

`POST /api/v1/ask` returns the same fields as the AI service's `AnswerResponse`, plus `id`. When the AI service cannot be reached the response is `503`; when it errors or returns an unusable payload it is `502`. In both cases the question is stored with state `FAILED`, so the admin area shows what visitors actually experienced.

## Layout

| Path | Purpose |
|---|---|
| `app/Services/Ai/` | `AiClient` is the only class that knows the AI service's URLs and wire format. `AiAnswer` validates its response. |
| `app/Actions/AskQuestion.php` | Calls the AI service and records the outcome. |
| `app/Enums/AnswerState.php` | The six AI states plus `FAILED`, with labels and the answered/unanswered grouping. |
| `app/Services/Analytics/QuestionAnalytics.php` | Daily aggregates and latency percentiles for the dashboards. |
| `app/Services/Analytics/QuestionInsights.php` | Sections, knowledge-gap groups, per-model quality, citation accuracy and transcription error. |
| `app/Services/Ai/KnowledgeBase.php` | Cached summary of what the AI service has indexed and which models it runs (`GET /v1/info`). Shared with every page. |
| `app/Console/Commands/DemoData.php` | `php artisan daleel:demo-data` creates flagged synthetic history; `--purge` removes it. |
| `resources/js/data/encyclopedia.json` | Book and chapter titles with their Dorar links, read once from the public table of contents. Source and date are recorded in the file. |
| `resources/js/lib/content.js` | Static content from the design: outcome texts, the 52 books, prepared example answers, and the advice shown beside misclassifications. No admin figures. |
| `app/Http/Controllers/Api/V1/` | Public API: ask, feedback, status. |
| `app/Http/Controllers/Admin/`, `Auth/` | Admin area and login. Public pages are plain `Route::inertia` routes. |
| `resources/js/pages/` | Inertia pages: `public/`, `auth/`, `admin/`. `layouts/` and `components/` hold the shared shell, answer card and charts. |
| `config/daleel.php` | Seeded admin, whether the login page shows its credentials, rate limit. |
| `config/services.php` (`ai`) | AI service URL, token, timeouts. |
| `docker/` | Container entrypoint and PHP settings. |

## Running

The whole stack starts from the repository root with `docker compose up --build`. See the root `RUNBOOK.md`.

On every start the container creates the `site` schema if needed, runs migrations, seeds the admin account from `ADMIN_EMAIL` / `ADMIN_PASSWORD`, and caches configuration. The application key is generated once and kept on a Docker volume unless `APP_KEY` is provided.

## Development

PHP does not need to be installed on the host. Build the toolchain image once, then run any Composer or Artisan command through it:

```powershell
docker build --target base -t daleel-site-dev apps/site
docker run --rm -v "${PWD}/apps/site:/app" daleel-site-dev composer install
docker run --rm -v "${PWD}/apps/site:/app" daleel-site-dev php artisan test
docker run --rm -v "${PWD}/apps/site:/app" daleel-site-dev ./vendor/bin/pint
```

Frontend assets use Node on the host:

```powershell
cd apps/site
npm install
npm run build
```

After changing PHP or Vue code, rebuild the running container with `docker compose up --build -d site`.

## Tests

`php artisan test` runs against in-memory SQLite with the AI service faked. It covers the proxy contract, failure handling, follow-ups, voice channel, feedback ownership, validation, rate limiting, CORS, login and lockout, admin-only access, dashboard aggregates, review queue filters and saving, the confusion matrix, the evaluation export and demo data.
