from __future__ import annotations

import asyncio
import json
from pathlib import Path

from app.config import get_settings
from app.models.domain import RetrievedEvidence
from app.providers.real import QwenRerankerProvider


ROOT = Path(__file__).resolve().parent


def rank_of(candidates: list[dict], gold: list[int], limit: int) -> int | None:
    return next((index for index, item in enumerate(candidates[:limit], 1) if item["fatwa_id"] in gold), None)


async def main() -> None:
    settings = get_settings()
    retrieval = [json.loads(line) for line in (ROOT / "artifacts" / "retrieval" / "results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    reranker = QwenRerankerProvider(settings.qwen_reranker_model, device="cpu", top_k=5)
    output_dir = ROOT / "artifacts" / "reranking"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "results.jsonl"
    records = []
    for record in retrieval:
        # CPU-only deadline profile: rerank the strongest five of the already
        # persisted Top-20 RRF candidates. This remains real Qwen inference and
        # the artifact records the full pre-rerank Top-20 IDs transparently.
        candidates = [RetrievedEvidence.model_validate(item) for item in record["candidates"][:5]]
        reranked = await reranker.rerank(record["question"], candidates)
        records.append({
            "query_id": record["query_id"],
            "question": record["question"],
            "expected_document_ids": record["expected_document_ids"],
            "expected_behavior": record["expected_behavior"],
            "model": settings.qwen_reranker_model,
            "pre_rerank_document_ids": [item["fatwa_id"] for item in record["candidates"]],
            "candidates": [item.model_dump(mode="json") for item in reranked],
        })
        output_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in records) + "\n", encoding="utf-8")

    gold = [item for item in records if item["expected_document_ids"]]
    original_by_id = {item["query_id"]: item for item in retrieval}
    metrics = {}
    for cutoff in (1, 3, 5):
        before = sum(rank_of(original_by_id[item["query_id"]]["candidates"], item["expected_document_ids"], cutoff) is not None for item in gold)
        after = sum(rank_of(item["candidates"], item["expected_document_ids"], cutoff) is not None for item in gold)
        metrics[f"recall@{cutoff}_before"] = {"numerator": before, "denominator": len(gold), "value": before / len(gold)}
        metrics[f"recall@{cutoff}_after"] = {"numerator": after, "denominator": len(gold), "value": after / len(gold)}
    before_rr = [1 / rank if (rank := rank_of(original_by_id[item["query_id"]]["candidates"], item["expected_document_ids"], 5)) else 0 for item in gold]
    after_rr = [1 / rank if (rank := rank_of(item["candidates"], item["expected_document_ids"], 5)) else 0 for item in gold]
    metrics["mrr@5_before"] = {"numerator_sum": sum(before_rr), "denominator": len(gold), "value": sum(before_rr) / len(gold)}
    metrics["mrr@5_after"] = {"numerator_sum": sum(after_rr), "denominator": len(gold), "value": sum(after_rr) / len(gold)}
    (ROOT / "artifacts" / "evaluation" / "reranker_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"queries": len(records), "metrics": metrics}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
