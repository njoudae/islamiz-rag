# Video Shot List — Maximum 2:00

| Time | Screen shown | Action | Voiceover | Overlay text |
|---|---|---|---|---|
| 0:00–0:15 | Home page, top | Slow scroll over the heading and the example answer | Problem segment | `المشكلة: الوصول + الثقة + السياق` |
| 0:15–0:30 | Home page → «اسأل دليل الآن» | Click through to the ask page | Solution segment | `لا مصدر = لا إجابة` |
| 0:30–0:45 | Ask page | Type «هل صلاة الجمعة فرض عين؟» and send; show the answer arriving | Demo, first part | `إجابة مباشرة` |
| 0:45–1:00 | The answer card, then Dorar | Point at the evidence, click «اقرأه في موضعه»; Dorar opens at the highlighted passage | Demo, second part | `الدليل بنصّه ورابطه` |
| 1:00–1:12 | Ask page | A question that needs one more fact; show the clarifying question and the reply | "When it does not answer", first part | `يحتاج توضيحاً` |
| 1:12–1:25 | Ask page | A question from a book that is not indexed, then a non-fiqh question | "When it does not answer", second part | `أدلة غير كافية · خارج النطاق` |
| 1:25–1:40 | Architecture diagram (`ARCHITECTURE.md`) | Trace the path from question to answer | "How it works" segment | `BGE-M3 → اختيار → توليد → تحقق` |
| 1:40–1:50 | Admin overview, then review queue | Show the question log and one review | Closing segment | `كل سؤال مسجّل وقابل للمراجعة` |

## Recording checks

- Target final duration: 1:40–1:55; hard limit: 2:00.
- Try every question once before recording. The answers come from a live model and take 7 to 11 seconds; cut the wait in editing.
- Voice questions need a Chromium-based browser and microphone permission.
- Do not show private browser tabs, credentials, local paths, or real visitors' questions. Record the admin area with the seeded demonstration data (`SEED_DEMO_DATA=true`).
- Use only questions written for the demo, such as the suggested ones in `JUDGING.md`; never a real visitor's question.
