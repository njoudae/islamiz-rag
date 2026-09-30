from __future__ import annotations

import asyncio
import csv
import json
from pathlib import Path

from app.config import get_settings
from app.providers.real import E5EmbeddingProvider
from app.repositories.postgres import PostgresFatwaRepository


ROOT = Path(__file__).resolve().parent


async def main() -> None:
    settings = get_settings()
    questions = [json.loads(line) for line in (ROOT / "evaluation" / "real_rag_questions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    repository = PostgresFatwaRepository(settings.database_url, E5EmbeddingProvider(settings.e5_model))
    output_dir = ROOT / "artifacts" / "retrieval"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "results.jsonl"
    records = []
    for item in questions:
        candidates = await repository.hybrid_search(item["question"], item["language"], limit=20)
        records.append({
            **item,
            "model": settings.e5_model,
            "fusion": "RRF(k=60)",
            "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
        })
        output_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in records) + "\n", encoding="utf-8")

    gold = [record for record in records if record["expected_document_ids"]]
    cutoffs = (1, 3, 5, 10, 20)
    metrics = {}
    for cutoff in cutoffs:
        hits = sum(any(candidate["fatwa_id"] in record["expected_document_ids"] for candidate in record["candidates"][:cutoff]) for record in gold)
        metrics[f"recall@{cutoff}"] = {"numerator": hits, "denominator": len(gold), "value": hits / len(gold) if gold else None}
    reciprocal = []
    for record in gold:
        rank = next((index for index, candidate in enumerate(record["candidates"][:10], 1) if candidate["fatwa_id"] in record["expected_document_ids"]), None)
        reciprocal.append(1 / rank if rank else 0)
    metrics["mrr@10"] = {"numerator_sum": sum(reciprocal), "denominator": len(gold), "value": sum(reciprocal) / len(gold) if gold else None}
    (ROOT / "artifacts" / "evaluation").mkdir(parents=True, exist_ok=True)
    (ROOT / "artifacts" / "evaluation" / "retrieval_metrics.json").write_text(json.dumps(metrics, ensure_ascii=False, indent=2), encoding="utf-8")

    csv_path = ROOT / "artifacts" / "evaluation" / "results.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=["query_id", "question", "expected_behavior", "gold_document_ids", "top_document_id", "gold_rank", "candidate_count"])
        writer.writeheader()
        for record in records:
            rank = next((index for index, candidate in enumerate(record["candidates"], 1) if candidate["fatwa_id"] in record["expected_document_ids"]), "")
            writer.writerow({
                "query_id": record["query_id"], "question": record["question"], "expected_behavior": record["expected_behavior"],
                "gold_document_ids": "|".join(map(str, record["expected_document_ids"])),
                "top_document_id": record["candidates"][0]["fatwa_id"] if record["candidates"] else "",
                "gold_rank": rank, "candidate_count": len(record["candidates"]),
            })
    print(json.dumps({"queries": len(records), "gold_queries": len(gold), "metrics": metrics}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
