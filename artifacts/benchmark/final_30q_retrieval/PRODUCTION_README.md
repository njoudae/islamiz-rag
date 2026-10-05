# Final Salah + Sawm Production RAG

## Decision

- Embedding: `BAAI/bge-m3`
- Representation: `D2` = normalized owner title + normalized own ruling
- Reranker: **NO** (no ranking gain; approximately 554 ms/query added)
- Retrieval: normalized question → BGE-M3 → cosine over all 584 units → Top-1
- Generation: fetch the selected unit's original ruling, attributions, consensus, evidence, wajh al-dalala, reasoning, and backend URL → one structured OpenAI Responses API call
- Endpoint: `POST /v1/ask`

GPT is not used for routing or issue selection. Citation URLs are attached by the backend from the selected stored unit.

## Environment

Required:

```text
OPENAI_API_KEY=...
```

Optional:

```text
OPENAI_GENERATION_MODEL=gpt-6.1-sol
RETRIEVAL_DEVICE=cuda
NEXT_PUBLIC_API_URL=http://localhost:8000
```

`RETRIEVAL_DEVICE` may be omitted for automatic device selection. The benchmark itself must use the CUDA command below.

## Commands

Benchmark/checkpoint resume:

```powershell
$env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; C:/Users/njood/anaconda3/envs/torch-gpu/python.exe run_final_30q_pipeline.py
```

API:

```powershell
$env:PYTHONPATH='apps/api'; apps/api/.venv-real/Scripts/python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend (second terminal):

```powershell
npm run dev -w @daleel/web
```

Smoke test:

```powershell
$env:PYTHONPATH='apps/api'; $env:HF_HUB_OFFLINE='1'; $env:TRANSFORMERS_OFFLINE='1'; apps/api/.venv-real/Scripts/python.exe scripts/final_rag_smoke_test.py
```

## Index files

- `production_index/embeddings.npy`
- `production_index/unit_ids.json`
- `production_index/units.jsonl`
- `production_index/manifest.json`

Each unit retains clean retrieval text separately from original source content and metadata. Explicit gender mentions are labeled only when literal source terms occur; no gender or madhhab ruling is inferred.
