# Limitations

- Daleel is a source-navigation assistant, not an independent mufti and not a substitute for a qualified scholar.
- The controlled corpus contains 40 Dorar Fiqh Encyclopedia documents and 88 chunks. It does not cover the full encyclopedia or arbitrary Islamic questions.
- The repository contains normalized source artifacts for inspection, but no open redistribution license for Dorar content has been identified. Public release of those corpus files requires a rights decision by the team.
- Arabic text questions are the verified path. Broad multilingual retrieval has not been evaluated.
- Voice endpoints and UI remain mock/experimental; browser microphone STT and production TTS are not part of the working text pipeline.
- E5 and Qwen run locally on CPU. First-request model loading and reranking can be slow and memory intensive.
- Qwen reranks the strongest five candidates from the persisted Top-20 hybrid retrieval set in the current deadline profile.
- OpenAI generation requires network access, a private API key, and available API quota. No key is stored in the repository.
- The evidence gate is heuristic. `ANSWERABLE` means retrieved evidence passed configured checks; it does not certify religious correctness.
- Conflict detection uses explicit source-language markers and does not perform general scholarly contradiction resolution.
- Real retrieval metrics use 10 authored test questions, eight with document labels. They are small-sample retrieval measures, not religious-accuracy or user-outcome measures.
- Deterministic safety tests and `evaluate.py` use mocks by design and must not be presented as real RAG accuracy.
- No production authentication, rate limiting, monitoring, backup, migration framework, or public deployment is included.
