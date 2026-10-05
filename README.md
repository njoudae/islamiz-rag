# دليل | Daleel

دليل هو مساعد أسئلة فقهية عربي يعتمد على مادة موثقة من **كتاب الصلاة** و**كتاب الصوم** في الموسوعة الفقهية للدرر السنية. يسترجع وحدات الحكم ذات الصلة، يختار فقط الوحدات التي تجيب عن السؤال، ثم يولّد جوابًا مقيدًا بالنص الأصلي مع مصادر يضيفها الخادم.

> هذا النظام أداة استرجاع وعرض للمادة المصدرية، وليس جهة إفتاء ولا بديلًا عن المختصين.

## المشكلة

السؤال بصياغة المستخدم لا يطابق دائمًا عنوان المسألة الفقهية، وقد يحتاج سؤال واحد إلى أكثر من وحدة. كما أن السماح للنموذج بالاعتماد على معرفته العامة قد يؤدي إلى حكم أو نسبة مذهب أو دليل غير موجود في المصدر. لذلك يفصل دليل بين الاسترجاع، والاختيار، والتوليد، ويجعل الخادم مالكًا للمصادر والأدلة المعروضة.

## المزايا الأساسية

- بحث دلالي عربي في 584 وحدة حكم قابلة للإجابة من الصلاة والصوم.
- دعم العربية الفصحى والصياغة السعودية/الخليجية في التقييم.
- اختيار وحدة واحدة أو عدة وحدات متكاملة من أعلى خمسة مرشحين.
- حالات صريحة: `ANSWER` و`CLARIFY` و`INSUFFICIENT_EVIDENCE` و`ESCALATE`.
- حفظ الحكم، ونسب المذاهب والعلماء، والإجماع، والأدلة، ووجه الدلالة، والمسار الهرمي، ورابط المصدر.
- عرض نص الدليل الأصلي من البيانات المخزنة؛ لا يُطلب من GPT إعادة كتابة الآية أو الحديث.
- تفضيلات اختيارية للغة والمذهب والجنس لا تتجاوز النص الصريح في المصدر.

## المعمارية ومسار RAG

```text
سؤال المستخدم
  → التطبيع العربي الموحد
  → BAAI/bge-m3 على تمثيل D2 (العنوان المنظف + الحكم المنظف)
  → cosine similarity على جميع الوحدات وعددها 584
  → Top-5 (لا BM25 ولا RRF ولا توجيه هرمي ولا reranker في الإنتاج)
  → selector منظم: ID + عنوان + حكم + مسار مختصر + نسب صريحة
                       + Evidence available/types/count فقط
  → وحدة واحدة أو عدة وحدات
  → جلب المحتوى الأصلي الكامل للوحدات المختارة فقط
  → GPT structured generation
  → تحقق الخادم من IDs ثم إرفاق المصادر والأدلة الأصلية
  → حفظ حالة المحادثة الخادمية بواسطة conversation_id
  → FastAPI POST /v1/ask → Laravel (سجل الأسئلة ولوحة الإدارة) → واجهة Vue
```

مسار السؤال النصي أعلاه حقيقي ومشترك بين الموقع و`POST /v1/ask`. السؤال الصوتي يُفرَّغ إلى نص في متصفح الزائر ثم يسلك المسار نفسه، وليس جزءًا من تقييم RAG.

التطبيع المستخدم للسؤال وللنص القابل للبحث هو NFKC، إزالة التشكيل والتطويل، توحيد أشكال الألف و`ى`، وتوحيد علامات الترقيم والمسافات. لا يوجد stemming أو تلخيص. النص الأصلي لا يتغير.

## قاعدة المعرفة

النسخة النهائية محصورة في كتابين فقط:

| الكتاب | الصفحات | العقد |
|---|---:|---:|
| كتاب الصلاة | 805 | 806 |
| كتاب الصوم | 142 | 142 |
| الإجمالي | 947 | 948 |

تحتوي البيانات على 596 حكمًا، بينما فهرس الإنتاج يضم 584 وحدة دلالية مستوفية لشروط البحث. الملفات المصدرية موجودة في `artifacts/dorar_final_dataset/four_books/`، والفهرس في `artifacts/benchmark/final_30q_retrieval/production_index/` بأبعاد `584 × 1024`.

## التشغيل السريع (Docker)

المتطلبات: Docker Desktop ومفتاح OpenAI فقط. لا حاجة لتثبيت Python أو Node أو PHP.

```powershell
Copy-Item .env.example .env     # macOS/Linux: cp .env.example .env
# عدّل .env وضع قيمة OPENAI_API_KEY
docker compose up --build
```

| الخدمة | الرابط |
|---|---|
| موقع الزائر | `http://localhost:8080` (صفحة التواصل `/contact`) |
| لوحة الإدارة | `http://localhost:8080/login` أو زر «دخول المشرفين» |

دخول الإدارة (حساب المشرف): `admin@daleel.sa` / `daleel-admin-2026`، وتعرضه صفحة الدخول مع زر تعبئة. الزائر العادي يستخدم الأداة دون تسجيل دخول. لملء لوحات الإدارة ببيانات تجريبية موسومة اضبط `SEED_DEMO_DATA=true` في `.env` قبل أول تشغيل.

عند أول تشغيل يُنزَّل نموذج التضمين `BAAI/bge-m3` تلقائيًا (نحو 2.3 جيجابايت) إلى وحدة تخزين Docker؛ انتظر ظهور `[daleel-ai] starting API` في السجل. فهرس الإنتاج والـprompts مضمّنة في الصورة ولا تحتاج بناءً. التفاصيل في [RUNBOOK.md](RUNBOOK.md).

المكوّنات: الموقع (`apps/site`، Laravel + Inertia + Vue: صفحات الزائر وواجهة API ولوحة الإدارة، وبياناته في PostgreSQL) ← خدمة الذكاء الاصطناعي (`apps/api`، FastAPI، تجيب من الفهرس الملفي). المتصفح لا يتصل بخدمة الذكاء الاصطناعي مباشرة، وكل سؤال يُسجَّل مع حالته وتقييم السائل في لوحة الإدارة.

## النماذج وقرار reranker

- Embedding: `BAAI/bge-m3`.
- التمثيل الفائز D2: `clean unit title + clean ruling`، نص واحد إلى متجه واحد.
- Generation: `gpt-6.1-sol` افتراضيًا عبر OpenAI Responses API ومخرجات منظمة.
- Reranker المقاس: `Qwen/Qwen3-Reranker-0.6B` على Top-10.
- قرار الإنتاج: **reranker معطل**؛ لم يحسن R@1 أو R@3 أو MRR، وأضاف متوسط 554.10 ms. بقيت المقاييس نفسها قبل/بعده، لذلك لا يُحمّل في طلبات الإنتاج.

## تقييم الاسترجاع

استُخدمت 30 مسألة ذهبية موثقة وثابتة: 15 صلاة و15 صوم، ولكل سؤال ID إجابة واحد. قورنت ثلاثة نماذج وثمانية تمثيلات بالبحث العالمي cosine على جميع الوحدات. أولوية الاختيار: R@10 ثم R@3 ثم MRR ثم R@1 ثم الزمن.

| النموذج/التمثيل الفائز | R@1 | R@3 | R@5 | R@10 | MRR | متوسط التضمين/سؤال |
|---|---:|---:|---:|---:|---:|---:|
| BGE-M3 / D2 | 0.900 | 1.000 | 1.000 | 1.000 | 0.9444 | 30.75 ms |

النتائج الكاملة: `artifacts/benchmark/final_30q_retrieval/FINAL_BENCHMARK.md` و`embedding_metrics.json` و`reranker_metrics.json`.

## تقييم التوليد النهائي

الاختبار النهائي يثبت BGE-M3/D2 وTop-5، ثم يختبر الفصحى والعامية، والجيران المتشابهين، والوحدة الواحدة، والوحدات المتعددة، والاستيضاح، وعدم كفاية المادة، والتصعيد، ونسب المذاهب، والدليل الحرفي. النجاح يتطلب الحالة الصحيحة، IDs المطلوبة، عدم اختراع IDs أو مذاهب، وبقاء الدليل المعروض مطابقًا لـ`text_original`.

| # | الحالة | المتوقع | الفعلي | الوحدات المختارة | النتيجة |
|---:|---|---|---|---|---|
| 1 | صلاة/فصحى/وحدة | ANSWER | ANSWER | nav-00506 | PASS |
| 2 | صوم/عامية/وحدة | ANSWER | ANSWER | nav-01556 | PASS |
| 3 | جار متشابه | ANSWER | ANSWER | nav-00836 | PASS |
| 4 | صلاة/وحدتان | ANSWER | ANSWER | nav-00831, nav-00835 | PASS |
| 5 | صوم/وحدتان | ANSWER | ANSWER | nav-01524, nav-01521 | PASS |
| 6 | معلومة ناقصة | CLARIFY | CLARIFY | — | PASS |
| 7 | خارج corpus | INSUFFICIENT_EVIDENCE | INSUFFICIENT_EVIDENCE | — | PASS |
| 8 | فتوى شخصية معقدة | ESCALATE | ESCALATE | — | PASS |
| 9 | مذاهب صريحة | ANSWER | ANSWER | nav-01498 | PASS |
| 10 | طلب دليل حرفي | ANSWER | ANSWER | nav-00895 | PASS |

النتيجة النهائية: **10/10 PASS**، بلا ادعاء مذهب غير مدعوم، أو تسريب/تحريف دليل، أو نصيحة خارجية في التصعيد. راجع `evaluation/generation_final_report.md`.

## تصميم الـprompts والـgrounding

النصان الكاملان المرجعيان هما `prompts/selector_prompt.txt` و`prompts/generation_prompt.txt`.

- الـselector لا يرى نصوص الأدلة؛ يرى `Evidence available: YES/NO` والأنواع والعدد، محسوبة حتميًا من بيانات الوحدة.
- المولّد يرى المحتوى الأصلي الكامل للوحدات المختارة فقط، ولا يختار قضية أخرى ولا يبحث خارجيًا.
- `CLARIFY`: سؤال واحد قصير عند غياب معلومة مادية يبين المصدر أنها تغير الحكم.
- `INSUFFICIENT_EVIDENCE`: عندما لا تدعم الوحدات المختارة جوابًا بلا تخمين.
- `ESCALATE`: رسالة محايدة فقط بأن المادة لا تكفي لحكم شخصي وأن الحالة تُحال إلى جهة مؤهلة؛ لا نصائح طبية أو قانونية أو طارئة من خارج السياق.
- الأدلة: GPT يعيد `evidence_ids` فقط؛ الخادم يتحقق منها ويعرض `text_original` ووجه الدلالة من السجل الأصلي. الروابط والاستشهادات ملك للـbackend.

### حالة المحادثة والاستيضاح

كل استجابة من `/v1/ask` تحتوي `conversation_id`. يحفظ الخادم في SQLite السؤال الأصلي، وسؤال الاستيضاح، والحالة، وسياق الوحدات ذات الصلة. إذا كانت الحالة `NEEDS_CLARIFICATION`، يرسل العميل الرد التالي مع `conversation_id` نفسه؛ يركّب الخادم السؤال الأصلي مع الرد ثم يعيد نفس مسار Top-5 والاختيار والتوليد. لا تُستخدم ذاكرة LLM. عند الوصول إلى جواب أو نتيجة نهائية تتغير الحالة من `awaiting_clarification` إلى `completed`. محادثات مختلفة لا تشترك في أي سياق.

## بنية المستودع

```text
apps/api/                 FastAPI، نماذج المجال، RAG، ingestion، والاختبارات
apps/site/                الموقع: Laravel 13 + Inertia + Vue 3 (صفحات الزائر، واجهة API، لوحة الإدارة)
artifacts/dorar_final_dataset/four_books/       corpus النهائي
artifacts/benchmark/final_30q_retrieval/        benchmark وفهرس الإنتاج
evaluation/               مجموعات ونتائج التقييم النهائية والتطويرية
prompts/                  prompts الإنتاج المرجعية
infra/schema.sql          مخطط PostgreSQL/pgvector لمسار ingestion القديم
run_final_30q_pipeline.py بناء benchmark والفهرس من dataset المخزن
scripts/run_generation_final_test_10.py          تقييم التوليد النهائي
```

## التشغيل اليدوي لخدمة الذكاء الاصطناعي

هذا المسار لتطوير خدمة الذكاء الاصطناعي وتقييمها فقط، ولا يمر عبر الموقع. المتطلبات:

- Python 3.11+
- ذاكرة كافية لتحميل BGE-M3؛ GPU اختياري للتشغيل، ومطلوب لإعادة benchmark الكامل كما يفرض السكربت.
- مفتاح OpenAI لمسار التوليد والتقييم النهائي.
- Docker Compose فقط إذا أردت تشغيل مخطط ingestion/PostgreSQL الاختياري.

من جذر المستودع في PowerShell:

```powershell
python -m venv apps/api/.venv-real
apps/api/.venv-real/Scripts/python -m pip install -e ".\apps\api[dev]"
# الخدمة تحمّل النموذج دون اتصال، فنزّله مرة واحدة أولًا
apps/api/.venv-real/Scripts/hf download BAAI/bge-m3
```

## متغيرات البيئة

| المتغير | المطلوب | الغرض |
|---|---|---|
| `OPENAI_API_KEY` | نعم للإجابة | مفتاح OpenAI؛ لا يُلتزم به في Git |
| `OPENAI_GENERATION_MODEL` | لا | الافتراضي `gpt-6.1-sol` |
| `FINAL_INDEX_DIR` | لا | مسار فهرس BGE-M3 النهائي |
| `CONVERSATION_DB_PATH` | لا | ملف SQLite لحالة المحادثات؛ الافتراضي `data/conversations.sqlite3` |
| `RETRIEVAL_DEVICE` | لا | `cpu` أو `cuda` أو فارغ للاختيار التلقائي |
| `INTERNAL_API_TOKEN` | عند النشر | سرّ مشترك يرسله الموقع في `X-Internal-Token`؛ يحمي `/v1/*`. في Docker يُضبط من `AI_SERVICE_TOKEN` |
| `APP_ENV` | لا | استخدم `production` في النشر؛ يعطل docs والصوت mock |
| `ALLOWED_ORIGINS` | عند النشر | JSON array لأصول CORS المسموحة |
| `DATABASE_URL` و`POSTGRES_*` | لمسار DB فقط | PostgreSQL/pgvector الاختياري |

`EMBEDDING_PROVIDER=bge_m3` و`RERANKER_PROVIDER=disabled` و`GENERATION_PROVIDER=openai` موثقة في `.env.example`. الصوت معطل افتراضيًا؛ mock لا يعمل عندما يكون `APP_ENV=production`.

## قاعدة البيانات وdata ingestion

`POST /v1/ask` يقرأ الفهرس الملفي النهائي مباشرة ولا يحتاج PostgreSQL. المخطط في `infra/schema.sql` يخص مسار ingestion التاريخي القابل لإعادة البناء، ويُنشأ اختياريًا عبر:

```powershell
docker compose up -d postgres
docker compose exec postgres psql -U daleel -d daleel -f /docker-entrypoint-initdb.d/001-schema.sql
```

الـcorpus النهائي مجمد ولا يحتاج scraping للتشغيل. لبناء benchmark والفهرس من `nodes.jsonl` المخزن، شغّل أمر التقييم أدناه. توجد أوامر ingestion القديمة تحت `daleel-ingest` للتجارب السابقة، لكنها ليست مصدر فهرس `/v1/ask` النهائي.

## التشغيل

```powershell
$env:PYTHONPATH="apps/api"
apps/api/.venv-real/Scripts/python -m uvicorn app.main:app --app-dir apps/api --host 127.0.0.1 --port 8000
```

اطرح الأسئلة من Swagger في بيئة التطوير على `http://127.0.0.1:8000/docs`. فحص API: `http://127.0.0.1:8000/health`. لا تطبع مفتاح OpenAI ولا تضع `.env` في Git.

## أوامر التقييم الدقيقة

إعادة تقييم الاسترجاع الكامل وإعادة بناء الفهرس مكلفة وتتطلب CUDA والنماذج الثلاثة:

```powershell
python run_final_30q_pipeline.py
```

تشغيل تقييم التوليد النهائي فقط (10 حالات، 20 استدعاء GPT):

```powershell
$env:PYTHONPATH="apps/api"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
apps/api/.venv-real/Scripts/python scripts/run_generation_final_test_10.py
```

لعرض النتائج افتح [`artifacts/evaluation/results.csv`](artifacts/evaluation/results.csv)، [`retrieval_metrics.json`](artifacts/evaluation/retrieval_metrics.json)، و[`reranker_metrics.json`](artifacts/evaluation/reranker_metrics.json). توليد GPT الحقيقي يحتاج `OPENAI_API_KEY` وقد يستهلك رصيد API؛ آخر النتائج الحقيقية محفوظة بالفعل في `artifacts/generation/`.

## الاختبارات

```powershell
# الموقع (Laravel)
docker build --target base -t daleel-site-dev apps/site
docker run --rm -v "${PWD}/apps/site:/app" daleel-site-dev sh -c "composer install --no-interaction && php artisan test"

# خدمة الذكاء الاصطناعي
apps/api/.venv-real/Scripts/python -m pytest apps/api/tests
apps/api/.venv-real/Scripts/python scripts/repository_audit.py
```

## مثال API

```http
POST /v1/ask
Content-Type: application/json

{
  "query": "هل صلاة الجمعة فرض عين؟ اذكر دليلًا من النص.",
  "language": "ar",
  "answer_mode": "text",
  "madhhab": null,
  "gender": null
}
```

شكل الاستجابة الفعلي:

```json
{
  "state": "ANSWERABLE",
  "language": "ar",
  "summary": "نعم، صلاة الجمعة فرض عين.",
  "explanation": "الوحدات المختارة: nav-00895",
  "clarification_question": null,
  "escalation_message": null,
  "conversation_id": "00000000-0000-0000-0000-000000000001",
  "citations": [
    {
      "fatwa_id": 1575,
      "title": "المَبحَثُ الثَّاني: حُكمُ صَلاةِ الجُمُعة",
      "source_url": "https://dorar.net/feqhia/1575",
      "excerpt": "صَلاةُ الجُمُعة فرْضُ عَينٍ.",
      "evidence": [{"evidence_id": "ev-nav-00895-001", "type": "quran", "text_original": "..."}]
    }
  ]
}
```

استجابة الاستيضاح الأولى:

```json
{
  "state": "NEEDS_CLARIFICATION",
  "language": "ar",
  "clarification_question": "هل مرضك يُرجى شفاؤه أم لا يُرجى شفاؤه؟",
  "citations": [],
  "conversation_id": "00000000-0000-0000-0000-000000000001"
}
```

يرسل العميل الرد مع المعرّف نفسه، ولا يرسله كسؤال مستقل:

```http
POST /v1/ask
Content-Type: application/json

{
  "query": "مرض مزمن ولا يرجى شفاؤه",
  "language": "ar",
  "conversation_id": "00000000-0000-0000-0000-000000000001"
}
```

يعيد الخادم بعد ذلك `ANSWERABLE` مع المعرّف نفسه والمصادر الداعمة، ويغلق حالة `awaiting_clarification`.

## نقاط API الرئيسية

- `GET /health`
- `POST /v1/ask`
- `GET /v1/info`: أسماء النماذج وحجم الفهرس المحمّل، للوحة الإدارة.
- `GET /v1/authority-contacts`
- `POST /v1/speech/transcribe` و`POST /v1/speech/synthesize`: تجريبيان، معطلان افتراضيًا وفي production.

## القيود

- النطاق كتابا الصلاة والصوم فقط؛ أي موضوع آخر يجب أن ينتهي إلى عدم كفاية المادة.
- المقاييس مبنية على 30 سؤال استرجاع و10 حالات توليد، وليست حكمًا على الصحة الشرعية العامة.
- selector والمولّد يعتمدان على OpenAI ويضيفان زمنًا وتكلفة؛ لا يوجد fallback توليدي محلي.
- خدمة الذكاء الاصطناعي محمية برمز داخلي فقط؛ دخول المشرف وتحديد معدل الطلبات في الموقع. لا يوجد نشر عام في هذا المستودع.
- بيانات الاتصال بالجهات المختصة فارغة حاليًا؛ لا تُخترع جهات أو أرقام.
- مخطط PostgreSQL يمثل مسار ingestion السابق ولا يخزن فهرس BGE-M3 النهائي ذي 1024 بعدًا.
- راجع `docs/sources-and-licenses.md` قبل توزيع نصوص المصدر، ولا يوجد ترخيص مشروع عام في المستودع.

## العمل المستقبلي

- توسيع corpus بعد تحقق مستقل دون تغيير النسخة النهائية الحالية.
- إضافة مصادقة وrate limiting ومراقبة تشغيلية.
- إضافة جهات إفتاء موثقة ومراجعة يدويًا لمسار التصعيد.
- توسيع مجموعات الاختبار باللهجات والحالات متعددة الوحدات.
- إعداد مزود صوت حقيقي عند الحاجة؛ الصوت ليس جزءًا من مسار النص الحالي.

## الفريق

- نجود بن إسحاق — مهندس ذكاء اصطناعي
- بشرى شودري — مهندس برمجيات

للتفاصيل: `evaluation/README.md` و`artifacts/benchmark/final_30q_retrieval/FINAL_BENCHMARK.md` و`artifacts/dorar_final_dataset/four_books/FINAL_REPORT.md`.
