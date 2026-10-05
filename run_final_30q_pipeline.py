from __future__ import annotations

import gc
import json
import os
import re
import time
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any

import numpy as np
import torch
from sentence_transformers import CrossEncoder, SentenceTransformer


ROOT = Path(__file__).resolve().parent
DATASET_DIR = ROOT / "artifacts" / "dorar_final_dataset" / "four_books"
OUTPUT_DIR = ROOT / "artifacts" / "benchmark" / "final_30q_retrieval"
GOLD_PATH = OUTPUT_DIR / "gold_questions.jsonl"
REPRESENTATIONS_PATH = OUTPUT_DIR / "representations.jsonl"
PRODUCTION_INDEX_DIR = OUTPUT_DIR / "production_index"
MODELS = {
    "multilingual_e5_small": "intfloat/multilingual-e5-small",
    "bge_m3": "BAAI/bge-m3",
    "qwen3_embedding_0_6b": "Qwen/Qwen3-Embedding-0.6B",
}
MODEL_LABELS = {
    "multilingual_e5_small": "multilingual-e5-small",
    "bge_m3": "BGE-M3",
    "qwen3_embedding_0_6b": "Qwen3-Embedding-0.6B",
}
REPRESENTATIONS = ("D0", "D1", "D2", "D3", "D4", "D5", "D6", "FULL")
ANSWERABLE_TYPES = {"mabhas", "matlab", "far", "masala", "other"}
ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")
BOOK_PREFIX = re.compile(r"^\s*كتاب\s+", re.UNICODE)
STRUCTURAL_PREFIX = re.compile(
    r"^\s*(?:الباب|الفصل|المبحث|المطلب|الفرع|المس(?:أ|ا)لة)"
    r"\s+[^:：\-–—]+\s*[:：\-–—]\s*",
    re.UNICODE,
)
TAMHID_PREFIX = re.compile(r"^\s*تمهيد\s*[:：\-–—]?\s*", re.UNICODE)


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    return [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_arabic(value: str) -> str:
    """The single retrieval normalizer, applied to queries and every indexed field."""
    value = unicodedata.normalize("NFKC", value or "")
    value = ARABIC_DIACRITICS.sub("", value).replace("ـ", "")
    value = value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    value = "".join(" " if unicodedata.category(ch)[0] in {"P", "S"} else ch for ch in value)
    return re.sub(r"\s+", " ", value).strip()


def explicit_gender_applicability(value: str) -> list[str]:
    """Record literal gender mentions only; this is not a ruling inference."""
    normalized = normalize_arabic(value)
    labels: list[str] = []
    if re.search(r"(?:^|\s)(?:المراة|النساء|الحامل|المرضع|الزوجة|المعتكفة)(?:\s|$)", normalized):
        labels.append("female_explicit")
    if re.search(r"(?:^|\s)(?:الرجل|الرجال|الزوج|المعتكف)(?:\s|$)", normalized):
        labels.append("male_explicit")
    return labels


def clean_hierarchy_title(value: str) -> str:
    # Keep the delimiter until the structural prefix has been removed. Running
    # punctuation normalization first would make the prefix expression consume
    # the meaningful title after the colon.
    value = unicodedata.normalize("NFKC", value or "")
    value = ARABIC_DIACRITICS.sub("", value).replace("ـ", "")
    value = value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    value = re.sub(r"\s+", " ", value).strip()
    previous = None
    while value and value != previous:
        previous = value
        value = BOOK_PREFIX.sub("", value, count=1)
        value = STRUCTURAL_PREFIX.sub("", value, count=1)
        value = TAMHID_PREFIX.sub("", value, count=1)
    return normalize_arabic(value)


def build_units(nodes: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = {node["id"]: node for node in nodes}
    units: list[dict[str, Any]] = []
    for node in nodes:
        ruling = (node.get("content") or {}).get("ruling")
        if node.get("type") not in ANSWERABLE_TYPES or not ruling or not ruling.get("original", "").strip():
            continue
        path_nodes: list[dict[str, Any]] = []
        current: dict[str, Any] | None = node
        seen: set[str] = set()
        while current and current["id"] not in seen:
            seen.add(current["id"])
            path_nodes.append(current)
            current = by_id.get(current.get("parent_id"))
        book = "sawm" if any("الصوم" in item["title_clean"] for item in path_nodes[-2:]) else "salah"
        positional_titles = [clean_hierarchy_title(item["title_original"]) for item in path_nodes]
        owner = positional_titles[0]
        ancestors = [title for title in positional_titles[1:] if title]
        clean_titles = [title for title in positional_titles if title]
        clean_ruling = normalize_arabic(ruling["original"])
        reps = {
            "D0": clean_ruling,
            "D1": owner,
            "D2": "\n".join([owner, clean_ruling]),
            "D3": "\n".join([*(ancestors[:1]), clean_ruling]),
            "D4": "\n".join([owner, *ancestors[:1], clean_ruling]),
            "D5": "\n".join([owner, *ancestors[:2], clean_ruling]),
            "D6": "\n".join([owner, *ancestors[:3], clean_ruling]),
            "FULL": "\n".join([owner, *ancestors, clean_ruling]),
        }
        units.append({
            "unit_id": node["id"],
            "source_id": node.get("source_id"),
            "book": book,
            "type": node["type"],
            "title_original": node["title_original"],
            "title_clean": owner,
            "hierarchy_original_leaf_to_root": [item["title_original"] for item in path_nodes],
            "hierarchy_clean_leaf_to_root": clean_titles,
            "source_url": node["source_url"],
            "ruling_original": ruling["original"],
            "ruling_clean": clean_ruling,
            "representations": reps,
        })
    return units


def encode_documents(model: SentenceTransformer, key: str, texts: list[str]) -> np.ndarray:
    kwargs: dict[str, Any] = {}
    values = texts
    if key == "multilingual_e5_small":
        values = [f"passage: {text}" for text in texts]
    elif key == "qwen3_embedding_0_6b":
        kwargs["prompt_name"] = "document"
    batch_size = 64 if key == "multilingual_e5_small" else 4
    return model.encode(
        values,
        batch_size=batch_size,
        normalize_embeddings=True,
        convert_to_numpy=True,
        show_progress_bar=False,
        **kwargs,
    ).astype("float32")


def encode_queries(model: SentenceTransformer, key: str, questions: list[str]) -> tuple[np.ndarray, list[float]]:
    vectors: list[np.ndarray] = []
    latencies: list[float] = []
    for question in questions:
        kwargs: dict[str, Any] = {}
        values = [f"query: {question}"] if key == "multilingual_e5_small" else [question]
        if key == "qwen3_embedding_0_6b":
            kwargs["prompt_name"] = "query"
        torch.cuda.synchronize()
        started = time.perf_counter()
        vector = model.encode(
            values,
            batch_size=1,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
            **kwargs,
        )[0].astype("float32")
        torch.cuda.synchronize()
        latencies.append((time.perf_counter() - started) * 1000)
        vectors.append(vector)
    return np.stack(vectors), latencies


def metric_summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    ranks = [row["gold_rank"] for row in rows]
    result: dict[str, Any] = {"questions": len(rows)}
    for cutoff in (1, 3, 5, 10):
        hits = sum(rank <= cutoff for rank in ranks)
        result[f"r@{cutoff}"] = hits / len(rows)
        result[f"r@{cutoff}_hits"] = hits
    result["mrr"] = sum(1.0 / rank for rank in ranks) / len(ranks)
    result["mean_latency_ms"] = float(np.mean([row["embedding_latency_ms"] for row in rows]))
    return result


def scoped_metrics(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "global": metric_summary(rows),
        "salah": metric_summary([row for row in rows if row["book"] == "salah"]),
        "sawm": metric_summary([row for row in rows if row["book"] == "sawm"]),
    }


def ranking_rows(
    questions: list[dict[str, Any]],
    units: list[dict[str, Any]],
    query_embeddings: np.ndarray,
    query_latencies: list[float],
    document_embeddings: np.ndarray,
    model_key: str,
    representation: str,
) -> list[dict[str, Any]]:
    unit_ids = [unit["unit_id"] for unit in units]
    rows: list[dict[str, Any]] = []
    for question, query_vector, latency in zip(questions, query_embeddings, query_latencies, strict=True):
        scores = document_embeddings @ query_vector
        order = np.argsort(-scores, kind="stable")
        gold_index = unit_ids.index(question["gold_unit_id"])
        gold_rank = int(np.flatnonzero(order == gold_index)[0]) + 1
        top = [
            {
                "rank": rank,
                "unit_id": unit_ids[index],
                "title": units[index]["title_original"],
                "score": float(scores[index]),
            }
            for rank, index in enumerate(order[:10], 1)
        ]
        rows.append({
            "question_id": question["id"],
            "book": question["book"],
            "question": question["question"],
            "gold_unit_id": question["gold_unit_id"],
            "model": model_key,
            "representation": representation,
            "gold_rank": gold_rank,
            "embedding_latency_ms": latency,
            "top_10": top,
        })
    return rows


def run_embedding_benchmark(units: list[dict[str, Any]], questions: list[dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    checkpoints = OUTPUT_DIR / "checkpoints_v2"
    checkpoints.mkdir(parents=True, exist_ok=True)
    all_rows: list[dict[str, Any]] = []
    metrics: dict[str, Any] = {
        "question_count": len(questions),
        "searchable_unit_count": len(units),
        "normalization": "NFKC + remove Arabic diacritics/tatweel + alef/ya mapping + punctuation/whitespace normalization",
        "rich_representation_equivalence": "Hierarchy + Unit Title + Ruling is exactly FULL; not duplicated.",
        "gpu": torch.cuda.get_device_name(0),
        "models": {},
    }
    normalized_questions = [normalize_arabic(item["question"]) for item in questions]
    for model_key, model_name in MODELS.items():
        print(f"Loading {model_name}", flush=True)
        model = SentenceTransformer(model_name, device="cuda", trust_remote_code=True)
        model.max_seq_length = min(int(model.max_seq_length), 1024)
        query_cache = checkpoints / f"{model_key}__queries.npz"
        if query_cache.exists():
            cached = np.load(query_cache)
            query_embeddings = cached["embeddings"]
            query_latencies = cached["latencies"].tolist()
        else:
            query_embeddings, query_latencies = encode_queries(model, model_key, normalized_questions)
            np.savez(query_cache, embeddings=query_embeddings, latencies=np.asarray(query_latencies, dtype="float32"))
        model_metrics: dict[str, Any] = {"model_name": model_name, "representations": {}}
        for representation in REPRESENTATIONS:
            embedding_path = checkpoints / f"{model_key}__{representation}.npy"
            if embedding_path.exists():
                document_embeddings = np.load(embedding_path)
            else:
                texts = [unit["representations"][representation] for unit in units]
                document_embeddings = encode_documents(model, model_key, texts)
                np.save(embedding_path, document_embeddings)
            rows = ranking_rows(
                questions, units, query_embeddings, query_latencies, document_embeddings, model_key, representation
            )
            all_rows.extend(rows)
            model_metrics["representations"][representation] = scoped_metrics(rows)
            summary = model_metrics["representations"][representation]["global"]
            print(model_key, representation, summary, flush=True)
            write_jsonl(OUTPUT_DIR / "embedding_results.jsonl", all_rows)
            metrics["models"][model_key] = model_metrics
            write_json(OUTPUT_DIR / "embedding_metrics.json", metrics)
        del model, query_embeddings
        gc.collect()
        torch.cuda.empty_cache()
    candidates: list[tuple[tuple[float, ...], str, str]] = []
    for model_key, model_data in metrics["models"].items():
        for representation, entry in model_data["representations"].items():
            value = entry["global"]
            priority = (value["r@10"], value["r@3"], value["mrr"], value["r@1"], -value["mean_latency_ms"])
            candidates.append((priority, model_key, representation))
    _, winning_model, winning_representation = max(candidates)
    metrics["winner"] = {
        "model_key": winning_model,
        "model_name": MODELS[winning_model],
        "representation": winning_representation,
        "selection_priority": ["R@10", "R@3", "MRR", "R@1", "latency"],
        "metrics": metrics["models"][winning_model]["representations"][winning_representation],
    }
    write_json(OUTPUT_DIR / "embedding_metrics.json", metrics)
    return metrics, all_rows


def run_reranker(
    units: list[dict[str, Any]], questions: list[dict[str, Any]], embedding_metrics: dict[str, Any], embedding_rows: list[dict[str, Any]]
) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    winner = embedding_metrics["winner"]
    model_key = winner["model_key"]
    representation = winner["representation"]
    baseline_rows = {
        row["question_id"]: row for row in embedding_rows
        if row["model"] == model_key and row["representation"] == representation
    }
    units_by_id = {unit["unit_id"]: unit for unit in units}
    reranker = CrossEncoder(
        "Qwen/Qwen3-Reranker-0.6B",
        device="cuda",
        max_length=512,
        trust_remote_code=True,
        model_kwargs={"torch_dtype": "auto"},
        tokenizer_kwargs={"padding_side": "left"},
    )
    results: list[dict[str, Any]] = []
    for question in questions:
        baseline = baseline_rows[question["id"]]
        candidate_ids = [item["unit_id"] for item in baseline["top_10"]]
        pairs = [(normalize_arabic(question["question"]), units_by_id[unit_id]["representations"][representation]) for unit_id in candidate_ids]
        torch.cuda.synchronize()
        started = time.perf_counter()
        raw_scores = reranker.predict(pairs, batch_size=2, show_progress_bar=False)
        torch.cuda.synchronize()
        reranker_latency = (time.perf_counter() - started) * 1000
        scores = np.asarray(raw_scores).reshape(-1)
        order = np.argsort(-scores, kind="stable")
        reranked_ids = [candidate_ids[index] for index in order]
        gold = question["gold_unit_id"]
        baseline_rank = baseline["gold_rank"]
        treatment_rank = reranked_ids.index(gold) + 1 if gold in reranked_ids else 11
        if baseline_rank != 1 and treatment_rank == 1:
            classification = "correction"
        elif treatment_rank > min(baseline_rank, 11):
            classification = "regression"
        else:
            classification = "unresolved"
        results.append({
            "question_id": question["id"],
            "book": question["book"],
            "question": question["question"],
            "gold_unit_id": gold,
            "candidate_coverage": gold in candidate_ids,
            "baseline_gold_rank": baseline_rank,
            "treatment_gold_rank": treatment_rank,
            "classification": classification,
            "embedding_latency_ms": baseline["embedding_latency_ms"],
            "reranker_latency_ms": reranker_latency,
            "total_latency_ms": baseline["embedding_latency_ms"] + reranker_latency,
            "baseline_top_10": baseline["top_10"],
            "reranked_top_10": [
                {"rank": rank, "unit_id": unit_id, "title": units_by_id[unit_id]["title_original"], "score": float(scores[index])}
                for rank, (index, unit_id) in enumerate(zip(order, reranked_ids, strict=True), 1)
            ],
        })
    baseline_metric_rows = [{"gold_rank": row["baseline_gold_rank"], "embedding_latency_ms": row["embedding_latency_ms"]} for row in results]
    treatment_metric_rows = [{"gold_rank": row["treatment_gold_rank"], "embedding_latency_ms": row["embedding_latency_ms"]} for row in results]
    baseline_metrics = metric_summary(baseline_metric_rows)
    treatment_metrics = metric_summary(treatment_metric_rows)
    baseline_metrics["reranker_latency_ms"] = 0.0
    baseline_metrics["total_latency_ms"] = baseline_metrics["mean_latency_ms"]
    treatment_metrics["reranker_latency_ms"] = float(np.mean([row["reranker_latency_ms"] for row in results]))
    treatment_metrics["total_latency_ms"] = float(np.mean([row["total_latency_ms"] for row in results]))
    candidate_coverage = sum(row["candidate_coverage"] for row in results) / len(results)
    no_primary_regression = (
        treatment_metrics["r@1"] >= baseline_metrics["r@1"]
        and treatment_metrics["r@3"] >= baseline_metrics["r@3"]
    )
    meaningful_improvement = no_primary_regression and (
        treatment_metrics["r@1"] > baseline_metrics["r@1"]
        or treatment_metrics["r@3"] > baseline_metrics["r@3"]
        or treatment_metrics["mrr"] >= baseline_metrics["mrr"] + 0.02
    )
    metrics = {
        "winning_embedding_model": model_key,
        "winning_representation": representation,
        "candidate_coverage_r@10_before_reranking": candidate_coverage,
        "baseline": baseline_metrics,
        "treatment": treatment_metrics,
        "corrections": [row["question_id"] for row in results if row["classification"] == "correction"],
        "regressions": [row["question_id"] for row in results if row["classification"] == "regression"],
        "unresolved": [row["question_id"] for row in results if row["classification"] == "unresolved"],
        "use_reranker": meaningful_improvement,
        "decision_rule": "Use only with higher R@1/R@3 or >=0.02 MRR gain, no R@1/R@3 regression; Top-10 candidates fixed.",
    }
    write_jsonl(OUTPUT_DIR / "reranker_results.jsonl", results)
    write_json(OUTPUT_DIR / "reranker_metrics.json", metrics)
    del reranker
    gc.collect()
    torch.cuda.empty_cache()
    return metrics, results


def build_production_index(units: list[dict[str, Any]], nodes: list[dict[str, Any]], embedding_metrics: dict[str, Any], reranker_metrics: dict[str, Any]) -> None:
    winner = embedding_metrics["winner"]
    checkpoint = OUTPUT_DIR / "checkpoints_v2" / f"{winner['model_key']}__{winner['representation']}.npy"
    embeddings = np.load(checkpoint)
    PRODUCTION_INDEX_DIR.mkdir(parents=True, exist_ok=True)
    np.save(PRODUCTION_INDEX_DIR / "embeddings.npy", embeddings)
    write_json(PRODUCTION_INDEX_DIR / "unit_ids.json", [unit["unit_id"] for unit in units])
    node_by_id = {node["id"]: node for node in nodes}
    records: list[dict[str, Any]] = []
    for unit in units:
        node = node_by_id[unit["unit_id"]]
        content = node["content"]
        records.append({
            "unit_id": unit["unit_id"],
            "source_id": unit["source_id"],
            "book": unit["book"],
            "type": unit["type"],
            "retrieval_text_clean": unit["representations"][winner["representation"]],
            "title_original": unit["title_original"],
            "title_clean": unit["title_clean"],
            "hierarchy_original_leaf_to_root": unit["hierarchy_original_leaf_to_root"],
            "hierarchy_clean_leaf_to_root": unit["hierarchy_clean_leaf_to_root"],
            "source_url": unit["source_url"],
            "ruling_original": unit["ruling_original"],
            "metadata": {
                "attributions": content.get("attributions", []),
                "consensus": content.get("consensus", []),
                "evidence_types": list(dict.fromkeys(item.get("type") for item in content.get("evidence", []))),
                "language": "ar",
                "gender_applicability": explicit_gender_applicability(
                    f"{unit['title_original']}\n{unit['ruling_original']}"
                ),
            },
            "authoritative_content": {
                "ruling": content.get("ruling"),
                "attributions": content.get("attributions", []),
                "consensus": content.get("consensus", []),
                "evidence": content.get("evidence", []),
                "reasoning": content.get("reasoning", []),
                "source_url": unit["source_url"],
            },
        })
    write_jsonl(PRODUCTION_INDEX_DIR / "units.jsonl", records)
    write_json(PRODUCTION_INDEX_DIR / "manifest.json", {
        "model_key": winner["model_key"],
        "model_name": winner["model_name"],
        "representation": winner["representation"],
        "normalization": embedding_metrics["normalization"],
        "unit_count": len(units),
        "embedding_shape": list(embeddings.shape),
        "reranker_enabled": reranker_metrics["use_reranker"],
        "reranker_model": "Qwen/Qwen3-Reranker-0.6B" if reranker_metrics["use_reranker"] else None,
        "scope": ["Kitab al-Salah", "Kitab al-Sawm"],
    })


def render_report(embedding: dict[str, Any], reranker: dict[str, Any], reranker_rows: list[dict[str, Any]]) -> None:
    winner = embedding["winner"]
    wm = winner["metrics"]["global"]
    before, after = reranker["baseline"], reranker["treatment"]
    lines = [
        "# Final 30-Question Retrieval Benchmark",
        "",
        "- Gold set: **30 verified questions** (15 Salah, 15 Sawm); the identical file was used by every experiment.",
        f"- Searchable semantic units: **{embedding['searchable_unit_count']}**.",
        f"- GPU: **{embedding['gpu']}**.",
        f"- Winner: **{MODEL_LABELS[winner['model_key']]} / {winner['representation']}**.",
        f"- Winner metrics: R@1 **{wm['r@1']:.3f}**, R@3 **{wm['r@3']:.3f}**, R@5 **{wm['r@5']:.3f}**, R@10 **{wm['r@10']:.3f}**, MRR **{wm['mrr']:.3f}**.",
        "- `Hierarchy + Unit Title + Ruling` is exactly equivalent to `FULL`; it was not duplicated.",
        "",
        "## Embedding results",
        "",
        "| Model | Representation | R@1 | R@3 | R@5 | R@10 | MRR | ms/query |",
        "|---|---|---:|---:|---:|---:|---:|---:|",
    ]
    for model_key, model in embedding["models"].items():
        for representation, scopes in model["representations"].items():
            value = scopes["global"]
            lines.append(
                f"| {MODEL_LABELS[model_key]} | {representation} | {value['r@1']:.3f} | {value['r@3']:.3f} | "
                f"{value['r@5']:.3f} | {value['r@10']:.3f} | {value['mrr']:.3f} | {value['mean_latency_ms']:.2f} |"
            )
    lines.extend([
        "", "## Salah / Sawm split", "",
        f"- Salah: {json.dumps(winner['metrics']['salah'], ensure_ascii=False)}",
        f"- Sawm: {json.dumps(winner['metrics']['sawm'], ensure_ascii=False)}",
        "", "## Qwen3-Reranker experiment", "",
        f"- Candidate R@10 before reranking: **{reranker['candidate_coverage_r@10_before_reranking']:.3f}**.",
        f"- Baseline: R@1 {before['r@1']:.3f}, R@3 {before['r@3']:.3f}, R@5 {before['r@5']:.3f}, R@10 {before['r@10']:.3f}, MRR {before['mrr']:.3f}, total {before['total_latency_ms']:.2f} ms.",
        f"- Treatment: R@1 {after['r@1']:.3f}, R@3 {after['r@3']:.3f}, R@5 {after['r@5']:.3f}, R@10 {after['r@10']:.3f}, MRR {after['mrr']:.3f}, reranker {after['reranker_latency_ms']:.2f} ms, total {after['total_latency_ms']:.2f} ms.",
        f"- Production reranker: **{'YES' if reranker['use_reranker'] else 'NO'}**.",
        "", "### Per-question reranker changes", "",
        "| Question | Class | Before rank | After rank |",
        "|---|---|---:|---:|",
    ])
    for row in reranker_rows:
        lines.append(f"| {row['question_id']} | {row['classification']} | {row['baseline_gold_rank']} | {row['treatment_gold_rank']} |")
    lines.extend([
        "", "## Production", "",
        f"- Flow: normalized query → {MODEL_LABELS[winner['model_key']]} ({winner['representation']}) → "
        + ("Top-10 → Qwen3-Reranker → Top-1" if reranker["use_reranker"] else "Top-1")
        + " → selected original authoritative unit → structured GPT answer.",
        "- Index: `artifacts/benchmark/final_30q_retrieval/production_index/`.",
        "- API: `POST /v1/ask`.",
        "- Required environment: `OPENAI_API_KEY`; optional `OPENAI_GENERATION_MODEL`.",
        "- Benchmark command: `C:/Users/njood/anaconda3/envs/torch-gpu/python.exe run_final_30q_pipeline.py`.",
    ])
    (OUTPUT_DIR / "FINAL_BENCHMARK.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
    if not torch.cuda.is_available():
        raise RuntimeError("CUDA GPU is required for the final benchmark")
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    nodes = read_jsonl(DATASET_DIR / "nodes.jsonl")
    questions = read_jsonl(GOLD_PATH)
    if len(questions) != 30 or Counter(item["book"] for item in questions) != Counter({"salah": 15, "sawm": 15}):
        raise ValueError("Gold set must contain exactly 15 Salah and 15 Sawm questions")
    units = build_units(nodes)
    unit_ids = {unit["unit_id"] for unit in units}
    missing = [item["gold_unit_id"] for item in questions if item["gold_unit_id"] not in unit_ids]
    if missing:
        raise ValueError(f"Gold IDs are not searchable units: {missing}")
    write_jsonl(REPRESENTATIONS_PATH, units)
    embedding_metrics, embedding_rows = run_embedding_benchmark(units, questions)
    reranker_metrics, reranker_rows = run_reranker(units, questions, embedding_metrics, embedding_rows)
    build_production_index(units, nodes, embedding_metrics, reranker_metrics)
    decision = {
        "WINNING_EMBEDDING_MODEL": embedding_metrics["winner"]["model_name"],
        "WINNING_REPRESENTATION": embedding_metrics["winner"]["representation"],
        "RERANKER": "YES" if reranker_metrics["use_reranker"] else "NO",
        "PRODUCTION_RETRIEVAL": (
            "Embedding -> Top-10 -> Qwen3-Reranker -> Top-1"
            if reranker_metrics["use_reranker"] else "Embedding -> Top-1"
        ),
        "measured_reason": {
            "baseline": reranker_metrics["baseline"],
            "treatment": reranker_metrics["treatment"],
            "candidate_coverage_r@10": reranker_metrics["candidate_coverage_r@10_before_reranking"],
            "decision_rule": reranker_metrics["decision_rule"],
        },
        "index_location": str(PRODUCTION_INDEX_DIR.relative_to(ROOT)).replace("\\", "/"),
    }
    write_json(OUTPUT_DIR / "PRODUCTION_DECISION.json", decision)
    write_jsonl(OUTPUT_DIR / "failures.jsonl", [])
    render_report(embedding_metrics, reranker_metrics, reranker_rows)
    print(json.dumps(decision, ensure_ascii=False, indent=2), flush=True)


if __name__ == "__main__":
    main()
