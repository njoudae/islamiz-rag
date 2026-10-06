# Limitations

## Scope

- Daleel is a source-navigation assistant, not an independent mufti and not a substitute for a qualified scholar.
- Answers come from two books of the Dorar Fiqh Encyclopedia only: Salah and Sawm, 584 ruling units. A fiqh question from any other book ends in `INSUFFICIENT_EVIDENCE`. The encyclopedia page on the site is a browsable index of all 52 books that links to Dorar; it does not mean all of them can be answered from.
- Not every page of the two books became a searchable unit. Some common questions inside them, for example eating forgetfully while fasting, have no unit and are refused.
- The repository contains extracted source text for inspection, but no open redistribution license for Dorar content has been identified. Public release of those files requires a rights decision by the team.
- Arabic questions, formal and Saudi/Gulf dialect, are the evaluated path. Other languages have not been evaluated.

## Answer pipeline

- The selector and the generator are OpenAI models. They need network access, a private API key and available quota, and they add time and cost: a typical answer takes 7 to 11 seconds. There is no local fallback for generation.
- `ANSWERABLE` means the selected units passed the pipeline's checks and every cited ID was verified by the server. It does not certify religious correctness.
- When scholars differ, the encyclopedia lists the opinions inside one unit and the answer presents them from that text. There is no separate "conflicting evidence" state.
- Attributions to a madhhab or scholar are extracted per unit, not per opinion. The site shows them only as part of the answer text.
- Clarification is driven by the selector, plus one fixed rule for illness and fasting. A follow-up continues the conversation only while its state is kept on the server.
- The out-of-scope check is a separate model call that can relabel a refusal. It never overrides a sourced answer.
- Referral in complex cases is a neutral message. No verified authority contacts are stored, and none are invented.

## Evaluation

- Retrieval was measured on 30 authored questions and generation on 10 authored cases. These are small samples that measure retrieval and grounding, not religious accuracy or user outcomes.
- The Python test suite still contains four tests written for the earlier experimental pipeline (`AnswerService`); they fail and do not describe the pipeline that serves answers.

## Voice

- Voice questions use the browser's own speech recognition (Web Speech API, Arabic). It works in Chromium-based browsers and sends audio to the browser vendor's service. When the browser has no recogniser or the microphone is blocked, the visitor is told why and asked to allow the microphone or type the question.
- Answers are not read aloud. The AI service's own speech endpoints are disabled.

## Website and admin area

- The admin figures come from the question log, the team's reviews and what the AI service reports. Citation accuracy, transcription error rate and the per-model quality rows stay empty until reviewers supply the input. Unanswered questions with no close unit fall into one "not covered" group.
- The "confidence" shown to reviewers is the similarity between the question and the nearest unit, not a probability that the answer is correct.
- The home page preview and the ask page's opening example are prepared answers, labelled as examples. When the AI service is offline the ask page answers from that small prepared set and labels each answer as prepared.
- Only the administrator signs in. Visitors are anonymous; a browser-generated identifier links a visitor's questions and feedback.

## Hosted demo

- The public demo runs on free tiers: the site and the AI service share one small container, and the database is hosted separately. The container sleeps when idle, so the first visit after a pause is slow.
- To fit that container, the demo embeds the question with the same BGE-M3 model hosted on Cloudflare Workers AI, so the question text leaves the server for that call. On the 30 benchmark questions this returned the same top five units in the same order as the local model. The Docker setup embeds locally.
- Conversation state for clarifications is kept in a file inside the container and is lost when it restarts. Questions, feedback and contact messages are kept in the database.
- There is no monitoring, backup or uptime guarantee.
