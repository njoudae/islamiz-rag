# Sources, Components, Services, and Licenses

Audited **2026-09-29**. `ACTUALLY USED` means imported, executed, or presented by the current repository. `PLANNED / OPTIONAL` means only a contract, schema, configuration placeholder, or local submission asset exists. No credentials belong in this file.

| Status | Component | Type | Source / version | Purpose | License / rights status | Restrictions / material notes | Access date |
|---|---|---|---|---|---|---|---|
| ACTUALLY USED | Daleel project code | First-party source | This repository | Product implementation | **No repository-level LICENSE file declared** | Copyright remains with its owners by default; choose and add a license only with all rights holders’ approval | 2026-09-29 |
| ACTUALLY USED | الموسوعة الفقهية – الدرر السنية | Approved knowledge reference | [dorar.net/feqhia](https://dorar.net/feqhia) | Default `OFFICIAL_HACKATHON_REFERENCE` source identity | No open redistribution license identified | Do not redistribute a copied corpus; preserve attribution/links; use only content the team is authorized to process | 2026-09-29 |
| ACTUALLY USED | Dorar methodology pages | Source methodology | [method](https://dorar.net/article/1923), [accreditation description](https://dorar.net/article/1983) | Understand source structure/method | Rights reserved; informational citation | No claim of partnership or endorsement | 2026-09-29 |
| ACTUALLY USED | Official challenge website | Competition source | [islamicaich.org](https://islamicaich.org/) | Tracks, participation, submission requirements | Rights reserved; informational citation | Official Arabic text controls; do not imply organizer endorsement | 2026-09-29 |
| ACTUALLY USED | Official participant guide | Competition PDF | [official PDF](https://islamicaich.org/files/Hackathon/i2xgA3mxVhrbRe0ReLlA86kTDbFZ9QQ9eb856dq8.pdf) | Deliverables and judging criteria | Rights reserved; participant information use | Summarized, not redistributed | 2026-09-29 |
| ACTUALLY USED | Official scientific annex | Competition reference policy | Participant portal; public website names the annex but exposes no indexed public content link | Approved-source scope | Organizer material | Team must confirm exact portal release before submission | 2026-09-29 |
| ACTUALLY USED | Next.js | Web framework | 16.3.5 | Web application | MIT | Preserve copyright/license notices | 2026-09-29 |
| ACTUALLY USED | React / React DOM | UI library | 19.3.0 | UI components | MIT | Preserve notices | 2026-09-29 |
| ACTUALLY USED | Lucide React | Icons | 0.468.0 | UI icons | ISC | Preserve notice | 2026-09-29 |
| ACTUALLY USED | Radix Slot | UI primitive | 1.3.3 | Component composition | MIT | Preserve notices | 2026-09-29 |
| ACTUALLY USED | clsx | Utility | 2.1.1 | CSS class composition | MIT | Preserve notices | 2026-09-29 |
| ACTUALLY USED | tailwind-merge | Utility | 2.6.1 | Merge utility classes | MIT | Preserve notices | 2026-09-29 |
| ACTUALLY USED | Tailwind CSS / PostCSS | Build tooling | Locked in `package-lock.json` | Styling build | MIT | Development/build dependency | 2026-09-29 |
| ACTUALLY USED | FastAPI | API framework | `>=0.115,<1` | HTTP API | MIT | Preserve notices | 2026-09-29 |
| ACTUALLY USED | Uvicorn | ASGI server | `>=0.32,<1` | Local API server | BSD-3-Clause | Preserve notices and non-endorsement clause | 2026-09-29 |
| ACTUALLY USED | Pydantic Settings | Configuration | `>=2.6,<3` | Environment parsing | MIT | Preserve notices | 2026-09-29 |
| ACTUALLY USED | SQLAlchemy | Database library | `>=2.0,<3` | Provider-ready database layer dependency | MIT | Runtime repository is not implemented | 2026-09-29 |
| ACTUALLY USED | psycopg / psycopg-binary | PostgreSQL driver | `>=3.2,<4` | Optional database connection | LGPL-3.0-only; recheck packaged notices | Review binary-distribution obligations before redistribution | 2026-09-29 |
| ACTUALLY USED | HTTPX | HTTP client | `>=0.27,<1` | Conservative source fetchers | BSD-3-Clause | Network access and source terms still apply | 2026-09-29 |
| ACTUALLY USED | Beautiful Soup | HTML parser | `>=4.12,<5` | Deterministic source parsing | MIT | Preserve notices | 2026-09-29 |
| ACTUALLY USED | python-multipart | Multipart parser | `>=0.0.20,<1` | Speech upload endpoint | Apache-2.0 | Preserve license/NOTICE when applicable | 2026-09-29 |
| ACTUALLY USED | Typer | CLI framework | `>=0.15,<1` | Ingestion CLI | MIT | Preserve notices | 2026-09-29 |
| ACTUALLY USED | pytest / pytest-asyncio / respx | Test tools | Dev ranges in `pyproject.toml` | Automated tests | Open-source; verify from installed distributions | Development only | 2026-09-29 |
| ACTUALLY USED | PostgreSQL | Database server | PostgreSQL 16-compatible container | Optional local schema | PostgreSQL License | No hosted service is bundled | 2026-09-29 |
| ACTUALLY USED | pgvector | PostgreSQL extension | `pgvector/pgvector:pg16` image | Vector column/index schema | PostgreSQL License | Schema exists; production vectors are not loaded | 2026-09-29 |
| ACTUALLY USED | Mock generation provider | First-party deterministic provider | `apps/api/app/providers/base.py` | Source-bound evaluation summary | Project code; repository-level license undeclared | Not an LLM; never represent it as model intelligence | 2026-09-29 |
| ACTUALLY USED | Mock reranker | First-party deterministic provider | Same module | Sort controlled candidate scores | Project code; repository-level license undeclared | Not a learned reranker | 2026-09-29 |
| ACTUALLY USED | Mock embedding provider | First-party deterministic provider | Same module | Ingestion contract/testing | Project code; repository-level license undeclared | Not semantic embeddings | 2026-09-29 |
| ACTUALLY USED | Mock ASR/TTS providers | First-party deterministic providers | Same module | API/provider contract tests | Project code; repository-level license undeclared | No real transcription or playable synthesized audio | 2026-09-29 |
| ACTUALLY USED | Application screenshots | First-party visual assets | `artifacts/screenshots/official/` | README/demo evidence | Created from Daleel UI | Ensure no third-party/private data enters replacement screenshots | 2026-09-29 |
| ACTUALLY USED | Team avatar SVGs | First-party visual assets | `assets/team-*.svg` | Presentation/team visuals | Project-owned or team-provided; provenance should be retained | Confirm creator/likeness permissions before public distribution | 2026-09-29 |
| ACTUALLY USED | GitHub QR image | Generated visual asset | `assets/github-qr.png` | Presentation repository link | Generated code image | Regenerate if final repository URL changes | 2026-09-29 |
| PLANNED / OPTIONAL | Ibn Baz website adapter | Isolated legacy source | [binbaz.org.sa](https://binbaz.org.sa/) | Non-default future collection only | No open data license identified | `BINBAZ_REFERENCE` is not an approved-source fallback; no corpus redistributed | 2026-09-29 |
| PLANNED / OPTIONAL | External embedding model | AI model | Not selected/connected | Semantic retrieval | Not applicable yet | Model name, license, hosting, data flow, and cost must be disclosed before use | 2026-09-29 |
| PLANNED / OPTIONAL | External reranker | AI model | Not selected/connected | Learned relevance scoring | Not applicable yet | Same disclosure requirement | 2026-09-29 |
| PLANNED / OPTIONAL | External LLM | AI model/service | Not selected/connected | Grounded summarization | Not applicable yet | No provider key or user/source content is currently sent externally | 2026-09-29 |
| PLANNED / OPTIONAL | Production ASR | AI model/service | Not selected/connected | Speech recognition | Not applicable yet | Requires audio privacy, retention, license, region, and accuracy review | 2026-09-29 |
| PLANNED / OPTIONAL | Production TTS | AI model/service | Not selected/connected | Spoken response | Not applicable yet | Must not impersonate a scholar/authority; disclose voice rights | 2026-09-29 |
| PLANNED / OPTIONAL | Official PowerPoint template | Organizer visual asset | Local participant asset | Submission presentation | Provided for challenge participation; no general license inferred | Final presentation artifact is not tracked yet | 2026-09-29 |

## Data and API disclosure

- No external AI/model API is called by the current runtime.
- No real beneficiary conversation dataset is used.
- Evaluation questions and HTML fixtures are synthetic.
- The real Dorar corpus is not committed.
- No credentials or populated `.env` file are committed.

## License blocker

The repository itself has no `LICENSE` file. That is not automatically a hackathon disqualifier, but it means downstream reuse rights are not granted by default and may reduce public-repository clarity. The team—not an automated tool—must choose the project license after confirming all contributors’ and prior-work rights.
