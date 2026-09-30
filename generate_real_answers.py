from __future__ import annotations

import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path

from app.api.routes import answer_service, settings
from app.models.domain import AskRequest, EvidenceState


ROOT = Path(__file__).resolve().parent


async def main() -> None:
    questions = [json.loads(line) for line in (ROOT / "evaluation" / "real_rag_questions.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    selected = [item for item in questions if item["query_id"] in {"q003", "q007", "q009"}]
    retrieval = {item["query_id"]: item for item in (json.loads(line) for line in (ROOT / "artifacts" / "retrieval" / "results.jsonl").read_text(encoding="utf-8").splitlines() if line.strip())}
    output = ROOT / "artifacts" / "generation" / "answers.jsonl"
    output.parent.mkdir(parents=True, exist_ok=True)
    records = []
    for item in selected:
        response = await answer_service.answer(AskRequest(query=item["question"], language=item["language"]))
        allowed_documents = {candidate["fatwa_id"] for candidate in retrieval[item["query_id"]]["candidates"]}
        cited_documents = [citation.fatwa_id for citation in response.citations]
        citation_valid = all(document_id in allowed_documents for document_id in cited_documents) and (
            response.state != EvidenceState.ANSWERABLE or bool(cited_documents)
        )
        records.append({
            "query_id": item["query_id"],
            "question": item["question"],
            "system_state": response.state.value,
            "retrieved_document_ids": [candidate["fatwa_id"] for candidate in retrieval[item["query_id"]]["candidates"]],
            "generated_answer": response.summary,
            "explanation": response.explanation,
            "citations": [citation.model_dump(mode="json") for citation in response.citations],
            "citation_valid": citation_valid,
            "clarification_question": response.clarification_question,
            "escalation_reason": response.escalation_message,
            "model": settings.openai_generation_model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        output.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in records) + "\n", encoding="utf-8")
    print(json.dumps({"answers": len(records), "answerable": sum(row["system_state"] == "ANSWERABLE" for row in records), "all_citations_valid": all(row["citation_valid"] for row in records)}, ensure_ascii=False))


if __name__ == "__main__":
    asyncio.run(main())
