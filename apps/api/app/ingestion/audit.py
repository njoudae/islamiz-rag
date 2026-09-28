import csv
import json
from collections import Counter
from pathlib import Path
from app.models.domain import FatwaDocument


def build_audit(documents: list[FatwaDocument], failures: list[dict] | None = None) -> dict:
    external_ids = [doc.external_id for doc in documents]
    counts = Counter(external_ids)
    categories = Counter(category for doc in documents for category in doc.category_path)
    collections = Counter(doc.source_collection.value for doc in documents)
    return {
        "total_fatwas": len(documents),
        "unique_fatwas": len(set(external_ids)),
        "duplicates": sum(count - 1 for count in counts.values() if count > 1),
        "fatwas_with_questions": sum(bool(doc.question) for doc in documents),
        "fatwas_without_questions": sum(not doc.question for doc in documents),
        "fatwas_with_audio": sum(doc.has_audio for doc in documents),
        "category_counts": dict(categories.most_common()),
        "source_collection_counts": dict(collections),
        "empty_answers": sum(not doc.answer.strip() for doc in documents),
        "very_short_answers": sum(0 < len(doc.answer.strip()) < 80 for doc in documents),
        "parsing_failures": len(failures or []),
        "failures": failures or [],
    }


def export_audit(audit: dict, json_path: Path, csv_path: Path) -> None:
    json_path.parent.mkdir(parents=True, exist_ok=True)
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    json_path.write_text(json.dumps(audit, ensure_ascii=False, indent=2), encoding="utf-8")
    rows = [(key, json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value) for key, value in audit.items()]
    with csv_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle)
        writer.writerow(["metric", "value"])
        writer.writerows(rows)
