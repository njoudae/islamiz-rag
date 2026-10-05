import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.models.domain import AnswerResponse, AskRequest, Citation, EvidenceState, RelatedSource, RetrievedEvidence
from app.providers.base import GenerationProvider, RerankerProvider
from app.rag.evidence import EvidenceSufficiencyEvaluator
from app.repositories.base import FatwaRepository
from app.services.query import QueryUnderstandingService

logger = logging.getLogger("daleel.pipeline")


class AnswerService:
    def __init__(self, repository: FatwaRepository, reranker: RerankerProvider, generator: GenerationProvider, persist_runtime_artifacts: bool = False):
        self.repository = repository
        self.reranker = reranker
        self.generator = generator
        self.understanding = QueryUnderstandingService()
        self.evaluator = EvidenceSufficiencyEvaluator()
        self.persist_runtime_artifacts = persist_runtime_artifacts

    async def answer(self, request: AskRequest) -> AnswerResponse:
        trace = {"trace_id": str(uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(), "question": request.query}
        analysis = await self.understanding.analyze(request.query, request.language)
        candidates = await self.repository.hybrid_search(request.query, analysis.language, analysis.category, source_collection=request.source_collection)
        trace["retrieved_chunks"] = [item.model_dump(mode="json") for item in candidates]
        self._persist_trace(trace)
        evidence = await self.reranker.rerank(request.query, candidates)
        trace["reranked_chunks"] = [item.model_dump(mode="json") for item in evidence]
        decision = self.evaluator.decide(analysis, evidence)
        trace["evidence_gate"] = decision.model_dump(mode="json")
        trace["final_evidence"] = [item.model_dump(mode="json") for item in evidence[:3]]
        self._persist_trace(trace)
        diagnostics = self._diagnostics(evidence, decision.reasons)
        if decision.state == EvidenceState.NEEDS_CLARIFICATION:
            response = AnswerResponse(state=decision.state, language=analysis.language, clarification_question=decision.clarification_question, **diagnostics)
            return self._finish(trace, response, citation_valid=True)
        if decision.state != EvidenceState.ANSWERABLE:
            message = "هذه المسألة تحتاج إلى تفاصيل أو نظر من مختص، ولم نجد في المصادر المتاحة ما يكفي لإعطائك جوابًا موثقًا."
            response = AnswerResponse(state=decision.state, language=analysis.language, escalation_message=message, **diagnostics)
            return self._finish(trace, response, citation_valid=True)

        generated = await self.generator.grounded_summary(request.query, evidence, analysis.language)
        trace["gpt"] = generated.model_dump(mode="json")
        self._persist_trace(trace)
        if generated.state != EvidenceState.ANSWERABLE:
            response = AnswerResponse(
                state=generated.state,
                language=analysis.language,
                clarification_question=generated.clarification_question,
                escalation_message=generated.escalation_reason,
                **{**diagnostics, "reasons": ["generation model judged the evidence insufficient for an answer"]},
            )
            return self._finish(trace, response, citation_valid=True)
        allowed = {item.chunk_id: item for item in evidence if item.chunk_id}
        if not generated.citation_chunk_ids or any(chunk_id not in allowed for chunk_id in generated.citation_chunk_ids):
            logger.warning("citation_validation %s", json.dumps({"valid": False, "returned": generated.citation_chunk_ids, "allowed": list(allowed)}, ensure_ascii=False))
            response = AnswerResponse(
                state=EvidenceState.INSUFFICIENT_EVIDENCE,
                language=analysis.language,
                escalation_message="رُفضت الإجابة لأن الاستشهادات لم تطابق الأدلة المسترجعة من المصدر المعتمد.",
                **{**diagnostics, "reasons": ["citations did not match the retrieved evidence"]},
            )
            return self._finish(trace, response, citation_valid=False)
        selected = []
        seen_documents: set[int] = set()
        for chunk_id in generated.citation_chunk_ids:
            item = allowed[chunk_id]
            if item.fatwa_id not in seen_documents:
                selected.append(item)
                seen_documents.add(item.fatwa_id)
        citations = [Citation(
            fatwa_id=item.fatwa_id,
            title=item.title,
            source_url=item.source_url,
            excerpt=item.excerpt,
            source_collection=item.source_collection,
            source_collection_name=item.source_collection_name,
            source_authority=item.source_authority,
            scholar=item.scholar,
            madhhabs=item.madhhabs,
            original_reference=item.original_reference,
            source_type=item.source_type,
            category_path=item.category_path,
        ) for item in selected[:3]]
        logger.info("citation_validation %s", json.dumps({"valid": True, "citation_chunk_ids": generated.citation_chunk_ids, "document_ids": [item.fatwa_id for item in selected]}, ensure_ascii=False))
        response = AnswerResponse(state=EvidenceState.ANSWERABLE, language=analysis.language, summary=generated.summary, explanation=generated.explanation, citations=citations, **diagnostics)
        return self._finish(trace, response, citation_valid=True)

    def _diagnostics(self, evidence: list[RetrievedEvidence], reasons: list[str]) -> dict:
        """What the pipeline looked at, for the website's analytics. Never shown as an answer."""
        return {
            "related": [
                RelatedSource(
                    fatwa_id=item.fatwa_id,
                    title=item.title,
                    source_url=item.source_url,
                    category_path=item.category_path,
                    reranker_score=item.reranker_score,
                )
                for item in evidence[:3]
            ],
            "evidence_score": max((item.reranker_score for item in evidence), default=None),
            "reasons": list(reasons),
            "model": getattr(self.generator, "model", None),
        }

    def _artifact_root(self) -> Path:
        return Path(__file__).resolve().parents[4] / "artifacts"

    def _persist_trace(self, trace: dict) -> None:
        if not self.persist_runtime_artifacts:
            return
        path = self._artifact_root() / "generation" / "latest_pipeline_trace.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(trace, ensure_ascii=False, indent=2), encoding="utf-8")

    def _finish(self, trace: dict, response: AnswerResponse, citation_valid: bool) -> AnswerResponse:
        if not self.persist_runtime_artifacts:
            return response
        trace["citation_validation"] = {"valid": citation_valid, "citations": [item.model_dump(mode="json") for item in response.citations]}
        trace["frontend_response"] = response.model_dump(mode="json")
        self._persist_trace(trace)
        answer_path = self._artifact_root() / "generation" / "answers.jsonl"
        with answer_path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps({
                "trace_id": trace["trace_id"], "question": trace["question"], "system_state": response.state.value,
                "generated_answer": response.summary, "citations": [item.model_dump(mode="json") for item in response.citations],
                "citation_valid": citation_valid, "model": getattr(self.generator, "model", None), "timestamp": trace["timestamp"],
            }, ensure_ascii=False) + "\n")
        return response
