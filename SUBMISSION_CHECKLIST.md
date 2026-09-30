# Submission Checklist

Statuses reflect repository evidence on 2026-09-29. Unchecked mandatory items block `READY`.

## Official deliverables

- [ ] Complete runnable product — **PARTIAL:** deterministic text scenario works; production retrieval/voice do not.
- [ ] Working live demo link — **MISSING.**
- [x] Operating documentation — `RUNBOOK.md`.
- [x] Sources/licenses record — `docs/sources-and-licenses.md`.
- [ ] Final presentation in PDF or PowerPoint — local ignored draft exists; final tracked/submitted artifact is missing.
- [ ] Video ≤ 2 minutes — script and shot list exist; recording is missing.
- [ ] Public GitHub repository for publishable code — remote configured; public visibility and final push must be confirmed.
- [x] No committed secrets detected by repository scan.
- [x] No prohibited real beneficiary conversations/data found; fixtures and golden cases are synthetic.
- [x] Approved knowledge-source collection is configured and Ibn Baz is isolated.
- [x] Reproducible one-command evaluation — `python evaluate.py`.
- [x] Team information included in `README.md`, `JUDGING.md`, and `submission.json`.

## Content and rights

- [x] No approved-reference corpus committed without established redistribution permission.
- [x] Used vs planned tools/models/services are distinguished.
- [ ] Team has confirmed every contributor’s rights and any employer/university/third-party approvals.
- [ ] Team has documented the pre-2026-10-04 baseline and the additions made during 2026-10-04 through 2026-10-06.
- [ ] Team has confirmed the exact scientific-annex release and approved source in the portal.

## Final technical verification

- [x] `python -m pytest apps/api/tests` passes: 30/30 on 2026-09-29.
- [x] `npm run build` passes, including TypeScript validation, on 2026-09-29.
- [x] `python evaluate.py` passes 8/8 and regenerates both evaluation artifacts.
- [x] Dependency audits completed: `npm audit` and `pip-audit` report no known vulnerabilities after updating the test-tool constraints.
- [x] Documentation links and referenced files pass `python scripts/repository_audit.py`.
- [x] `submission.json` and evaluation JSON files parse successfully.
- [ ] Live deployment, all routes, and source links have been checked immediately before submission.

## Portal and judging operations

- [ ] Submit through the official portal by **2026-10-06 23:59 Riyadh time (UTC+3)**.
- [ ] Retain the submission confirmation.
- [ ] Ensure the live service will stay awake and accessible during review.
- [ ] Prepare the selected-finalist format: five-minute presentation plus three-minute questions.
- [ ] If a general portal outage blocks delivery, follow the official documented incident process; do not send credentials or keys.
