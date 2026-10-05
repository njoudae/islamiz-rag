# Claim → Evidence Matrix

Claims are intentionally narrower than aspirations. `IMPLEMENTED` means executable code or a verifiable artifact exists; `PARTIAL` means only a bounded subset exists; `PLANNED` means an interface/schema or design exists without an active integration.

| Claim | Status | Evidence |
|---|---|---|
| Targets **الحوار المعرفي والإجابات الموثوقة** | IMPLEMENTED | `submission.json`, `JUDGING.md` |
| Uses the approved Dorar Fiqh Encyclopedia collection by default | IMPLEMENTED | `apps/api/app/models/domain.py`, `apps/api/app/ingestion/adapters.py`, `apps/site/resources/js/lib/content.js` |
| Ibn Baz is not the default or fallback | IMPLEMENTED | `SourceCollection`, `adapter_for`, `DemoFatwaRepository`; test coverage in `test_submission_safety.py` |
| “No Source = No Answer” | IMPLEMENTED | `AnswerResponse.no_answer_without_source`, `FinalRagService.answer`, final generation regression |
| Original source identity is preserved | IMPLEMENTED | `FatwaDocument`, `FatwaChunk`, `Citation`; adapter/chunk/source tests |
| Original cleaned source text is preserved separately from retrieval normalization | IMPLEMENTED | `full_original_text`, `retrieval_text`, content hash; `test_original_source_text_is_preserved` |
| Missing context produces a clarification | IMPLEMENTED | `QueryUnderstandingService`, `EvidenceSufficiencyEvaluator`, `test_missing_context_requests_clarification` |
| Insufficient evidence does not generate a ruling | IMPLEMENTED | `FinalRagService`, final generation regression case 07 |
| Complex cases are escalated | IMPLEMENTED | complexity flags and `COMPLEX_CASE`; corresponding test |
| Conflicting evidence is not merged | IMPLEMENTED | `conflicting_positions` gate and `test_conflicting_evidence_is_not_merged` |
| Out-of-scope questions do not generate fatwas | IMPLEMENTED | intent routing and `test_out_of_scope_does_not_generate_fatwa` |
| Unverified contact details are hidden | IMPLEMENTED | `EmptyContactRepository`, verified-contact schema, test |
| Arabic text query path works | IMPLEMENTED | Next.js ask page → `/v1/ask`; evaluation cases A–C |
| English query path works | PARTIAL | narrow term-based recognition and deterministic English summary; case G and `test_cross_language_retrieval` |
| Multilingual interaction is broad | PLANNED | no translation or cross-lingual model connected |
| Voice interaction works end to end | PARTIAL | provider interfaces, API endpoints, and mocks exist; browser recording/playback not connected |
| Hybrid retrieval is active in production | PLANNED | repository contract and PostgreSQL lexical/vector indexes exist; active repository is deterministic demo |
| Semantic embeddings are active | PLANNED | `EmbeddingProvider` and deterministic mock only |
| Learned reranking is active | PLANNED | `RerankerProvider` and score sorting mock only |
| Grounded LLM generation is active | PLANNED | `GenerationProvider` and deterministic template only |
| PostgreSQL/pgvector schema exists | IMPLEMENTED | `infra/schema.sql`, `docker-compose.yml` |
| Production database-backed retrieval works | PLANNED | no database repository/loader in runtime |
| Source ingestion does not bypass access controls | IMPLEMENTED | robots-aware crawler fails closed on blocking; `docs/discovery.md` |
| Full approved-source corpus is included | PLANNED / RESTRICTED | intentionally absent pending redistribution rights; synthetic fixtures only |
| Reproducible offline evaluation exists | IMPLEMENTED | `python evaluate.py`, golden set, JSON/Markdown outputs |
| Public deployment exists | PLANNED | no live URL in repository |
| Presentation exists in submission package | NOT YET | local ignored deck only; must add/submit final approved artifact |
| ≤2-minute video exists | NOT YET | script and shot list only |
