# Official Hackathon Requirements

Checked against the live official website and official participant guide on **2026-09-29**. `PASS` means repository evidence exists; it does not mean the submission portal has accepted the item.

## Official sources

- [Official challenge website](https://islamicaich.org/)
- [Official participant guide (44-page PDF)](https://islamicaich.org/files/Hackathon/i2xgA3mxVhrbRe0ReLlA86kTDbFZ9QQ9eb856dq8.pdf)
- [Official terms and conditions](https://islamicaich.org/terms)
- Official scientific annex in the participant portal. The public website identifies this annex as controlling scientific material but does not expose an indexed public link to its contents.

## Requirement matrix

| Requirement | Official source | How Daleel satisfies it | Evidence/path | Status |
|---|---|---|---|---|
| Target one official track | Website “مسارات التحدي”; guide pp. 6–11 | Targets the exact first-track title | `JUDGING.md`, `submission.json` | PASS |
| Track: **الحوار المعرفي والإجابات الموثوقة** | Guide p. 7 | Conversational retrieval, source citation, clarification/referral | `apps/api/app/services/answers.py`, `apps/api/app/rag/evidence.py` | PASS |
| Track success: answer is correct/clear/contextual, traceable to approved source, and system refuses/refers without sufficient reference | Guide p. 7 | Traceability and refusal/referral are enforced and tested; religious correctness over a full corpus is not established | `apps/api/tests/test_submission_safety.py`, `evaluation/REPORT.md` | PARTIAL |
| Complete working product, not an idea or incomplete prototype | Website participation rules; guide pp. 13, 29 | UI and API run; central deterministic scenario works. Production retrieval and real voice are not connected | `RUNBOOK.md`, `LIMITATIONS.md` | PARTIAL |
| Live demo link, fully working and available for review | Guide pp. 13, 30 | No public deployment URL is recorded | `LIMITATIONS.md` | MISSING |
| Public GitHub repository containing all code the team may publish | Website; guide pp. 13, 30 | A GitHub remote is configured, but public visibility cannot be proven from repository files alone | `.git/config` local evidence; submission portal must verify URL | PARTIAL |
| Operating/setup documentation | Website; guide p. 30 | Copy-paste run, test, DB, ingestion, and shutdown instructions | `RUNBOOK.md`, `README.md` | PASS |
| No secrets, passwords, real beneficiary records, or unauthorized components | Website; guide pp. 13, 30–31 | Ignore rules, placeholder env, tests and scan; fixtures/questions are synthetic | `.gitignore`, `.env.example`, `apps/api/tests/fixtures/`, `apps/api/tests/test_submission_safety.py` | PASS |
| Use synthetic or fully anonymized data only | Website participation rules | Golden set and HTML fixtures are synthetic; no real conversation dataset is present | `evaluation/evaluation_cases.json`, `apps/api/tests/fixtures/` | PASS |
| Content and scientific sources documented and verified | Guide p. 13 | Default source identity and deterministic adapter are documented; corpus is not redistributed | `docs/sources-and-licenses.md`, `docs/discovery.md` | PASS |
| Approved-source requirement from scientific annex | Terms §2 and §7; guide pp. 7, 20 | `OFFICIAL_HACKATHON_REFERENCE` maps to the Dorar Fiqh Encyclopedia; Ibn Baz is isolated | `apps/api/app/models/domain.py`, `apps/api/app/ingestion/adapters.py` | PASS |
| Confirm the exact annex/source release used | Official scientific annex | The repository records the reference and access date, but does not include the official annex file/link for independent verification | `docs/sources-and-licenses.md` | PARTIAL |
| Source/license/tool/model/service disclosure | Website; guide pp. 13, 30 | Used and planned components are separated with licenses/restrictions/access date | `docs/sources-and-licenses.md` | PASS |
| Rights for third-party code, content, data, assets, and prior work | Website; terms §8 | Open-source licenses and source restrictions are recorded; final rights confirmation remains a team/portal declaration | `docs/sources-and-licenses.md` | PARTIAL |
| Presentation in PDF or PowerPoint | Guide pp. 13, 29 | A presentation exists in local ignored build output, but no final tracked submission artifact is present | `.deck_output/` (local/ignored) | MISSING |
| Presentation covers problem, solution, mechanism, value, technologies, project images | Guide p. 29 | Existing local deck requires final content review before submission | `docs/CLAIM_EVIDENCE_MATRIX.md` supports review | PARTIAL |
| Presentation may be Arabic or English and may use official or identity-compliant custom template | Website FAQ; guide p. 29 | Arabic RTL presentation work exists locally; final tracked artifact missing | `.deck_output/` | PARTIAL |
| Explanatory video no longer than two minutes | Website; guide pp. 13, 31 | Script and shot list prepared; video not recorded | `docs/VIDEO_SCRIPT_AR.md`, `docs/VIDEO_SHOTLIST.md` | MISSING |
| Submission via portal by 2026-10-06 23:59 Riyadh time | Website; guide pp. 26, 28 | Cannot be completed or verified from this repository | `SUBMISSION_CHECKLIST.md` | MISSING |
| Retain submission confirmation | Website | External action after portal submission | `SUBMISSION_CHECKLIST.md` | MISSING |
| Existing project: document baseline before 2026-10-04, disclose components/rights, and identify work done during 4–6 October | Website FAQ; terms §8 | Git history records pre-challenge state; no explicit baseline/additions statement yet | Git history | PARTIAL |
| Final judging: technical solution and AI use — 25% | Guide pp. 35–36 | Architecture, tests, deterministic query/evidence logic; external AI providers remain mocks | `ARCHITECTURE.md`, `LIMITATIONS.md` | PARTIAL |
| Final judging: scientific reliability and safety — 15% | Guide p. 35–36 | No-source invariant, source preservation, conflict/complex routing | `apps/api/tests/test_submission_safety.py`, `evaluation/REPORT.md` | PASS |
| Final judging: innovation and added value — 15% | Guide pp. 35, 37 | Source-preserving access flow and evidence gate are demonstrated; no comparative user study | `JUDGING.md`, `docs/DEMO.md` | PARTIAL |
| Final judging: beneficiary experience, communication, accessibility — 10% | Guide pp. 35, 37 | RTL responsive UI and clear states; no target-user usability study and voice is mock | `apps/web/`, `artifacts/screenshots/official/` | PARTIAL |
| Final judging: benefit against track success criterion — 20% | Guide pp. 35, 38 | Routing/citation metrics exist; no full-corpus correctness or user-outcome measure | `evaluation/REPORT.md` | PARTIAL |
| Final judging: operating and continuation realism — 10% | Guide pp. 35, 38 | Runbook, schema, boundaries, provider plan; no deployment/cost/maintenance evidence | `RUNBOOK.md`, `ARCHITECTURE.md`, `LIMITATIONS.md` | PARTIAL |
| Final judging: presentation clarity and verifiability — 5% | Guide pp. 35, 39 | Judge guide, claim matrix, one-command evaluation | `JUDGING.md`, `docs/CLAIM_EVIDENCE_MATRIX.md`, `evaluate.py` | PASS |
| Final judging session: five minutes presentation plus three minutes questions if selected | Guide p. 34 | Team preparation item outside repository execution | `SUBMISSION_CHECKLIST.md` | MISSING |
| Human decisions; automated tools only assist evaluation | Terms §11 | Repository contains no evaluator manipulation and makes claims evidence-verifiable | `docs/CLAIM_EVIDENCE_MATRIX.md` | PASS |

## Official final judging weights

| Criterion | Weight |
|---|---:|
| جودة الحل التقني وتوظيف الذكاء الاصطناعي | 25% |
| الموثوقية والسلامة العلمية | 15% |
| الابتكار والقيمة المضافة | 15% |
| تجربة المستفيد والتواصل والإتاحة | 10% |
| تحقيق النفع وفق معيار نجاح المسار | 20% |
| واقعية التشغيل والاستكمال | 10% |
| وضوح العرض وإتاحة التحقق | 5% |

## Submission package required by the official guide

1. Complete runnable product.
2. Working live demo link.
3. Public GitHub repository containing publishable code and documentation.
4. Operating/setup documentation and source/tool/license record.
5. PDF or PowerPoint presentation.
6. Explanatory video of no more than two minutes.
7. Scientific/content source documentation.
8. Portal submission before the official deadline and retained confirmation.

