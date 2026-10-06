# Evaluation

يفصل هذا المجلد بين **التقييم النهائي للإنتاج** وبين تجارب التطوير الأقدم. لا تُفسَّر ملفات التطوير القديمة على أنها المقاييس النهائية.

## ما الذي يُقيّم؟

1. الاسترجاع: قدرة النموذج/التمثيل على ترتيب وحدة الإجابة الذهبية ضمن جميع وحدات الصلاة والصوم.
2. التوليد: صحة اختيار وحدة أو عدة وحدات، والحالة المنظمة، والتقيد بالمصدر، وسلامة نسب المذاهب، والحفاظ الحرفي على الأدلة التي يعرضها الخادم.

## تقييم الاسترجاع النهائي

- 30 سؤالًا موثقًا: 15 صلاة و15 صوم.
- لكل سؤال `gold_unit_id` واحد.
- نفس الأسئلة لكل نموذج وتمثيل.
- بحث cosine عالمي بلا BM25 أو RRF أو selector أثناء benchmark.
- الفائز: `BAAI/bge-m3` مع D2 (`clean title + clean ruling`).
- R@1 = 0.900، R@3 = 1.000، R@5 = 1.000، R@10 = 1.000، MRR = 0.9444.
- Qwen3-Reranker لم يغير المقاييس وأضاف 554.10 ms في المتوسط؛ لذلك هو معطل في الإنتاج.

المدخلات والنتائج الخام موجودة تحت `artifacts/benchmark/final_30q_retrieval/`، وأهمها `gold_questions.jsonl` و`embedding_results.jsonl` و`embedding_metrics.json` و`reranker_results.jsonl` و`reranker_metrics.json`.

لتشغيل benchmark كاملًا من جذر المستودع، داخل بيئة Python تحتوي PyTorch/CUDA والنماذج المطلوبة:

```powershell
python run_final_30q_pipeline.py
```

هذا الأمر مكلف ويعيد جميع تجارب models × representations؛ لا يلزم لتشغيل التطبيق.

## تقييم التوليد النهائي

المجموعة ثابتة من 10 حالات صعبة: صلاة وصوم، فصحى وعامية، جار متشابه، وحدة واحدة، وحدات متعددة، استيضاح، عدم كفاية، تصعيد، مذاهب صريحة، ودليل أصلي.

PASS يعني أن:

- الحالة الفعلية تطابق المتوقعة.
- كل ID مختار من Top-5 وتوجد الوحدات المطلوبة.
- عدد الوحدات ضمن الحد المتوقع.
- لا يوجد ID دليل مختلق أو نسبة مذهب غير موجودة في السياق.
- لا يعيد GPT نص الدليل داخل `answer`؛ الخادم يعرض سجل `text_original`.
- الدليل ووجه الدلالة المعروضان لم يتغيرا.
- التصعيد لا يحتوي نصيحة طبية أو طارئة أو ادعاء خارجيًا.

النتيجة النهائية: **10 PASS / 0 FAIL**.

```powershell
$env:PYTHONPATH="apps/api"
$env:HF_HUB_OFFLINE="1"
$env:TRANSFORMERS_OFFLINE="1"
apps/api/.venv-real/Scripts/python scripts/run_generation_final_test_10.py
```

يتطلب الأمر `OPENAI_API_KEY`، ويشغل 10 حالات فقط. الملفات النهائية:

- `generation_final_results.json`: Top-5، والاختيار، والسياق الكامل المختار، والمخرج المنظم، والتحققات.
- `generation_final_report.md`: عرض يدوي لكل الحالات العشر.

## اختبارات المسار الإنتاجي

`apps/api/tests/test_final_pipeline.py` و`apps/api/tests/test_api_routes.py` تغطي ما يضمنه الخادم نفسه دون تحميل نموذج أو اتصال بالشبكة: إرفاق المصدر ونص الدليل الأصلي، رفض معرّف دليل أو وحدة مختلق، غياب الجواب عند غياب مزود التوليد، سؤال الاستيضاح ومتابعته بالـ`conversation_id` نفسه، الإحالة، حالة «خارج النطاق»، والرمز الداخلي.

```powershell
apps/api/.venv-real/Scripts/python -m pytest apps/api/tests
```

## تجارب التطوير

ملفات مثل `evaluation_cases.json` و`results.json` و`REPORT.md` و`real_rag_questions.jsonl`، وكذلك مجلدات `artifacts/evaluation/` و`artifacts/generation_final_test_10/`، تسجل مراحل وتجارب سابقة. حُفظت للتدقيق ولم تُحذف، لكنها ليست بديلًا عن التقييم النهائي أعلاه.
