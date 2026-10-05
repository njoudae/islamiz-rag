# Final 30-Question Retrieval Benchmark

- Gold set: **30 verified questions** (15 Salah, 15 Sawm); the identical file was used by every experiment.
- Searchable semantic units: **584**.
- GPU: **NVIDIA GeForce RTX 4060 Laptop GPU**.
- Winner: **BGE-M3 / D2**.
- Winner metrics: R@1 **0.900**, R@3 **1.000**, R@5 **1.000**, R@10 **1.000**, MRR **0.944**.
- `Hierarchy + Unit Title + Ruling` is exactly equivalent to `FULL`; it was not duplicated.

## Embedding results

| Model | Representation | R@1 | R@3 | R@5 | R@10 | MRR | ms/query |
|---|---|---:|---:|---:|---:|---:|---:|
| multilingual-e5-small | D0 | 0.433 | 0.633 | 0.800 | 0.900 | 0.589 | 27.38 |
| multilingual-e5-small | D1 | 0.533 | 0.667 | 0.733 | 0.800 | 0.628 | 27.38 |
| multilingual-e5-small | D2 | 0.633 | 0.900 | 0.967 | 0.967 | 0.778 | 27.38 |
| multilingual-e5-small | D3 | 0.533 | 0.733 | 0.833 | 0.967 | 0.674 | 27.38 |
| multilingual-e5-small | D4 | 0.567 | 0.933 | 0.967 | 0.967 | 0.736 | 27.38 |
| multilingual-e5-small | D5 | 0.700 | 0.900 | 0.967 | 0.967 | 0.804 | 27.38 |
| multilingual-e5-small | D6 | 0.700 | 0.867 | 0.967 | 0.967 | 0.802 | 27.38 |
| multilingual-e5-small | FULL | 0.700 | 0.900 | 0.967 | 0.967 | 0.806 | 27.38 |
| BGE-M3 | D0 | 0.633 | 1.000 | 1.000 | 1.000 | 0.806 | 30.75 |
| BGE-M3 | D1 | 0.700 | 0.867 | 0.900 | 0.933 | 0.787 | 30.75 |
| BGE-M3 | D2 | 0.900 | 1.000 | 1.000 | 1.000 | 0.944 | 30.75 |
| BGE-M3 | D3 | 0.767 | 0.967 | 1.000 | 1.000 | 0.869 | 30.75 |
| BGE-M3 | D4 | 0.867 | 0.967 | 1.000 | 1.000 | 0.925 | 30.75 |
| BGE-M3 | D5 | 0.767 | 0.967 | 1.000 | 1.000 | 0.864 | 30.75 |
| BGE-M3 | D6 | 0.800 | 1.000 | 1.000 | 1.000 | 0.900 | 30.75 |
| BGE-M3 | FULL | 0.833 | 1.000 | 1.000 | 1.000 | 0.917 | 30.75 |
| Qwen3-Embedding-0.6B | D0 | 0.733 | 0.833 | 0.900 | 0.967 | 0.797 | 91.76 |
| Qwen3-Embedding-0.6B | D1 | 0.400 | 0.633 | 0.667 | 0.767 | 0.534 | 91.76 |
| Qwen3-Embedding-0.6B | D2 | 0.800 | 0.900 | 1.000 | 1.000 | 0.869 | 91.76 |
| Qwen3-Embedding-0.6B | D3 | 0.733 | 0.933 | 0.967 | 0.967 | 0.826 | 91.76 |
| Qwen3-Embedding-0.6B | D4 | 0.767 | 0.900 | 0.967 | 1.000 | 0.854 | 91.76 |
| Qwen3-Embedding-0.6B | D5 | 0.733 | 0.900 | 0.933 | 1.000 | 0.830 | 91.76 |
| Qwen3-Embedding-0.6B | D6 | 0.800 | 0.900 | 0.933 | 1.000 | 0.863 | 91.76 |
| Qwen3-Embedding-0.6B | FULL | 0.767 | 0.900 | 0.933 | 1.000 | 0.847 | 91.76 |

## Salah / Sawm split

- Salah: {"questions": 15, "r@1": 0.8666666666666667, "r@1_hits": 13, "r@3": 1.0, "r@3_hits": 15, "r@5": 1.0, "r@5_hits": 15, "r@10": 1.0, "r@10_hits": 15, "mrr": 0.9333333333333333, "mean_latency_ms": 38.08131999491403}
- Sawm: {"questions": 15, "r@1": 0.9333333333333333, "r@1_hits": 14, "r@3": 1.0, "r@3_hits": 15, "r@5": 1.0, "r@5_hits": 15, "r@10": 1.0, "r@10_hits": 15, "mrr": 0.9555555555555556, "mean_latency_ms": 23.428540001623333}

## Qwen3-Reranker experiment

- Candidate R@10 before reranking: **1.000**.
- Baseline: R@1 0.900, R@3 1.000, R@5 1.000, R@10 1.000, MRR 0.944, total 30.75 ms.
- Treatment: R@1 0.900, R@3 1.000, R@5 1.000, R@10 1.000, MRR 0.944, reranker 554.10 ms, total 584.85 ms.
- Production reranker: **NO**.

### Per-question reranker changes

| Question | Class | Before rank | After rank |
|---|---|---:|---:|
| salah-01 | unresolved | 1 | 1 |
| salah-02 | correction | 2 | 1 |
| salah-03 | regression | 1 | 3 |
| salah-04 | unresolved | 1 | 1 |
| salah-05 | unresolved | 1 | 1 |
| salah-06 | unresolved | 2 | 2 |
| salah-07 | unresolved | 1 | 1 |
| salah-08 | unresolved | 1 | 1 |
| salah-09 | unresolved | 1 | 1 |
| salah-10 | unresolved | 1 | 1 |
| salah-11 | unresolved | 1 | 1 |
| salah-12 | regression | 1 | 2 |
| salah-13 | unresolved | 1 | 1 |
| salah-14 | unresolved | 1 | 1 |
| salah-15 | unresolved | 1 | 1 |
| sawm-01 | unresolved | 1 | 1 |
| sawm-02 | unresolved | 1 | 1 |
| sawm-03 | unresolved | 1 | 1 |
| sawm-04 | unresolved | 1 | 1 |
| sawm-05 | unresolved | 1 | 1 |
| sawm-06 | unresolved | 1 | 1 |
| sawm-07 | unresolved | 1 | 1 |
| sawm-08 | unresolved | 1 | 1 |
| sawm-09 | unresolved | 1 | 1 |
| sawm-10 | unresolved | 1 | 1 |
| sawm-11 | unresolved | 1 | 1 |
| sawm-12 | unresolved | 1 | 1 |
| sawm-13 | unresolved | 1 | 1 |
| sawm-14 | correction | 3 | 1 |
| sawm-15 | unresolved | 1 | 1 |

## Production

- Flow: normalized query → BGE-M3 (D2) → Top-1 → selected original authoritative unit → structured GPT answer.
- Index: `artifacts/benchmark/final_30q_retrieval/production_index/`.
- API: `POST /v1/ask`.
- Required environment: `OPENAI_API_KEY`; optional `OPENAI_GENERATION_MODEL`.
- Benchmark command: `C:/Users/njood/anaconda3/envs/torch-gpu/python.exe run_final_30q_pipeline.py`.

## Integrated smoke test

- Result: **6/6 passed**.
- Covered: Salah formal, Salah Saudi colloquial, Sawm formal, Sawm colloquial, a difficult near-neighbor, and an out-of-corpus fiqh question.
- The five in-scope retrieval checks selected their expected unit IDs.
- The out-of-corpus Zakat question returned `INSUFFICIENT_EVIDENCE`.
- All returned citation URLs came from the backend production index; none were generated by GPT.
- Full machine-readable results: `smoke_test_results.json`.

See `PRODUCTION_README.md` for the exact API/frontend commands and environment variables.
