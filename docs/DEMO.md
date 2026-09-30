# 60–90 Second Demo

Use synthetic questions only. Start the API and UI using `RUNBOOK.md`, or show the same behavior through `python evaluate.py` if the UI is unavailable.

## 0:00–0:15 — Grounded answer

Ask:

> أنا مسافر وسأقيم أربعة أيام، هل أقصر الصلاة؟

Show the `ANSWERABLE` screen, the source card, collection identity, and original Dorar URL. Explain that the displayed summary is not an independent ruling.

## 0:15–0:30 — Retrieval trace

Point to the four displayed stages: question understanding, approved-source search, reranking, and evidence sufficiency. Open the original-source view and show that source identity and reference metadata remain separate from the AI explanation.

## 0:30–0:50 — Missing context

Ask:

> أنا مسافر، هل أقصر الصلاة؟

Show `NEEDS_CLARIFICATION` and the grounded question asking for intended stay duration. Emphasize that the system does not guess the missing circumstance.

## 0:50–1:10 — Unsupported/complex safety

Ask:

> لدي مسألة ميراث شخصية متشعبة بين ورثة متعددين، ما الحكم النهائي؟

Show `COMPLEX_CASE`, no generated ruling, and specialist referral. Then mention that unverified contact data is deliberately not displayed.

## 1:10–1:25 — Reproducibility

Run:

```bash
python evaluate.py
```

Open `evaluation/REPORT.md` and show total/passed cases, routing rates, source-preservation rate, and fabricated citation count.

## Demo guardrails

- Do not imply production voice, a full indexed corpus, or an external LLM is connected.
- Do not state a preferred religious ruling.
- If a live service fails, show the deterministic evaluation rather than substituting pre-recorded output as a live result.

