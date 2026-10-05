# Limitations

- Daleel is a source-navigation assistant, not an independent mufti and not a substitute for a qualified scholar.
- The controlled corpus contains 40 Dorar Fiqh Encyclopedia documents and 88 chunks. It does not cover the full encyclopedia or arbitrary Islamic questions.
- The repository contains normalized source artifacts for inspection, but no open redistribution license for Dorar content has been identified. Public release of those corpus files requires a rights decision by the team.
- Arabic text questions are the verified path. Broad multilingual retrieval has not been evaluated.
- Voice questions use the browser's own speech recognition (Web Speech API, Arabic). It works in Chromium-based browsers and sends audio to the browser vendor's service. When the browser has no recogniser or the microphone is blocked, the visitor is told why and asked to allow the microphone or type the question; nothing is sent. The AI service's STT/TTS endpoints remain mock, and answers are not read aloud.
- The admin figures come from the question log, the team's reviews and what the AI service reports. Three of them stay empty until reviewers supply the input: citation accuracy, transcription error rate, and the per-model quality rows. Unanswered questions with no close passage fall into one "not covered" group, because the AI service does not cluster questions by topic.
- The home page preview and the ask page's opening example are prepared answers, labelled as examples. When the AI service is offline the ask page answers from that small prepared set and labels each answer as demo mode.
- E5 and Qwen run locally on CPU. First-request model loading and reranking can be slow and memory intensive.
- Qwen reranks the strongest five candidates from the persisted Top-20 hybrid retrieval set in the current deadline profile.
- OpenAI generation requires network access, a private API key, and available API quota. No key is stored in the repository.
- The evidence gate is heuristic. `ANSWERABLE` means retrieved evidence passed configured checks; it does not certify religious correctness.
- Conflict detection uses explicit source-language markers and does not perform general scholarly contradiction resolution.
- Real retrieval metrics use 10 authored test questions, eight with document labels. They are small-sample retrieval measures, not religious-accuracy or user-outcome measures.
- Deterministic safety tests and `evaluate.py` use mocks by design and must not be presented as real RAG accuracy.
- No production authentication, rate limiting, monitoring, backup, migration framework, or public deployment is included.
