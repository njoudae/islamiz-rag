# دليل

## Official Track

**الحوار المعرفي والإجابات الموثوقة**

## Problem

المادة الإسلامية الموثوقة موجودة، لكن الوصول إلى النص المناسب يحتاج غالبًا معرفة المصطلح وبنية المرجع. الأسئلة العامية أو الناقصة تزيد خطر إرجاع نص غير ملائم أو إجابة غير مسندة.

## Solution

دليل واجهة عربية أولًا تستقبل سؤالًا نصيًا، تفهم موضوعه وتفاصيله المؤثرة، وتسترجع مادة من مجموعة المصدر المعتمدة المحددة. يمر الدليل المسترجع عبر بوابة كفاية قبل إنشاء شرح موجز مرتبط بالمصدر. عند نقص السياق يسأل النظام سؤالًا توضيحيًا؛ وعند غياب الدليل أو تعارضه أو تعقّد الحالة يمتنع عن الحكم ويحيل إلى مختص.

## Core Principle

**NO SOURCE = NO ANSWER**

تقنيًا، لا تسمح `AnswerResponse` بالحالة `ANSWERABLE` دون ملخص واستشهاد واحد على الأقل. ويمنع `EvidenceSufficiencyEvaluator` التوليد قبل اجتياز شروط التغطية، ودرجة إعادة الترتيب، واتساق الأدلة. غياب المصدر ينتج `INSUFFICIENT_EVIDENCE` بلا ملخص ولا استشهاد.

## Why AI?

- فهم اللغة الطبيعية والأسئلة العامية.
- العربية هي المسار المجرّب؛ الدعم متعدد اللغات غير مثبت بالتقييم الحالي.
- تضمينات `multilingual-e5-small` حقيقية واسترجاع دلالي + معجمي مدمج بـRRF داخل PostgreSQL/pgvector.
- استخراج السياق المؤثر مثل مدة السفر.
- إعادة ترتيب أعلى خمسة مرشحين فعليًا بواسطة `Qwen3-Reranker-0.6B`.
- تقدير كفاية الدليل عبر عدة إشارات.
- توليد GPT فعلي مقيد بالدليل مع تحقق لاحق من معرّفات المقاطع المستشهد بها.
- واجهات ASR/TTS منفذة بعقود مزود وتجربة mock فقط، وليست صوتًا إنتاجيًا.

## Approved Knowledge Source

المجموعة الافتراضية هي **الموسوعة الفقهية – الدرر السنية** (`OFFICIAL_HACKATHON_REFERENCE`). corpus مضبوط من 40 مستندًا حقيقيًا و88 مقطعًا. محول ابن باز معطل عن المسار الافتراضي.

## End-to-End Flow

Question → Query Understanding → Approved Source → Hybrid Retrieval → Reranking → Evidence Gate → Answer / Clarification / Escalation → Citation

## Implemented

- FastAPI endpoint للسؤال وعقود النص/الصوت.
- فهم استعلام عربي واستخراج بعض التفاصيل المؤثرة.
- مستودع PostgreSQL يحتوي مستندات ومقاطع Dorar الحقيقية وتضمينات E5.
- استرجاع dense + lexical، دمج RRF، وإعادة ترتيب Qwen محلية.
- توليد OpenAI GPT مقيد بالأدلة وتحقق من الاستشهاد.
- محول حتمي لصفحات `dorar.net/feqhia` يحفظ النص والهوية والمراجع الصريحة.
- حالات: `ANSWERABLE`, `NEEDS_CLARIFICATION`, `INSUFFICIENT_EVIDENCE`, `COMPLEX_CASE`, `CONFLICTING_EVIDENCE`, `OUT_OF_SCOPE`.
- شرط برمجي يمنع إجابة `ANSWERABLE` بلا استشهاد.
- واجهة Next.js عربية RTL تتصل بـ API لمسار السؤال النصي.
- اختبارات سلامة حتمية منفصلة وتقييم RAG حقيقي موثق في `artifacts/`.

## Provider-Ready / Planned

- ASR وTTS إنتاجيان وتوصيل تسجيل الصوت في المتصفح.
- دعم لغات واسع وتوجيه حقيقي متعدد اللغات.
- نشر عام وقرار حقوق صريح لنشر corpus المصدر.

## Safety

- `ANSWERABLE`: دليل مباشر قوي ومتسق؛ يسمح بملخص واستشهاد.
- `NEEDS_CLARIFICATION`: تفصيل مؤثر مفقود؛ يطلب سؤالًا واحدًا.
- `INSUFFICIENT_EVIDENCE`: لا دليل مباشر كافٍ؛ لا يولد حكمًا.
- `COMPLEX_CASE`: حالة شخصية عالية السياق؛ إحالة لمختص.
- `CONFLICTING_EVIDENCE`: لا يدمج مواقف متعارضة في حكم واحد.
- `OUT_OF_SCOPE`: سؤال خارج نطاق الاسترجاع الفقهي؛ لا يصدر فتوى.

## How to Run

راجع [RUNBOOK.md](RUNBOOK.md). تشغيل المسار الحقيقي يتطلب PostgreSQL وOpenAI وموديلات Hugging Face المحلية.

```powershell
docker compose up -d postgres
apps/api/.venv-real/Scripts/python -m uvicorn app.main:app --app-dir apps/api --port 8000
npm run dev
```

## How to Evaluate

```powershell
$env:PYTHONPATH="apps/api"
apps/api/.venv-real/Scripts/python evaluate_real_rag.py
apps/api/.venv-real/Scripts/python rerank_real_rag.py
```

`evaluate.py` منفصل وحتمي ويختبر سلوك السلامة باستخدام mocks؛ لا يمثل دقة RAG الحقيقية.

## Team

نجود بن إسحاق — مهندس ذكاء اصطناعي  
بشرى شودري — مهندس برمجيات
