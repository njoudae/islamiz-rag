"""Deprecated pre-final hybrid pipeline retained for historical experiment scripts.

Production routes must use :class:`app.services.final_rag.FinalRagService`.
This module is not imported by the API, frontend, workers, or background jobs.
"""

import json
import logging
import warnings
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app.models.domain import AnswerResponse, AskRequest, Citation, EvidenceState
from app.providers.base import GenerationProvider, RerankerProvider, RoutingEvidenceProvider
from app.rag.evidence import EvidenceSufficiencyEvaluator
from app.repositories.base import FatwaRepository
from app.services.query import QueryUnderstandingService

logger = logging.getLogger("daleel.pipeline")


class AnswerService:
    def __init__(self, repository: FatwaRepository, reranker: RerankerProvider | None, generator: GenerationProvider, persist_runtime_artifacts: bool = False, routing_evidence: RoutingEvidenceProvider | None = None):
        warnings.warn(
            "AnswerService is a legacy experiment pipeline; production uses FinalRagService.",
            DeprecationWarning,
            stacklevel=2,
        )
        self.repository = repository
        self.reranker = reranker
        self.generator = generator
        self.understanding = QueryUnderstandingService()
        self.evaluator = EvidenceSufficiencyEvaluator()
        self.persist_runtime_artifacts = persist_runtime_artifacts
        self.routing_evidence = routing_evidence

    async def answer(self, request: AskRequest) -> AnswerResponse:
        trace = {"trace_id": str(uuid4()), "timestamp": datetime.now(timezone.utc).isoformat(), "question": request.query}
        if self.routing_evidence is not None:
            scope = await self.routing_evidence.classify_scope(request.query, request.language)
            trace["scope_routing"] = {"provider": "gpt", "classification": scope}
            if scope == "NON_FIQH":
                response = AnswerResponse(
                    state=EvidenceState.OUT_OF_SCOPE,
                    language=request.language or "ar",
                    escalation_message="هذا ليس من اختصاصي، أنا أجيب فقط عن المسائل الفقهية.",
                )
                return self._finish(trace, response, citation_valid=True)
        analysis = await self.understanding.analyze(request.query, request.language)
        candidates = await self.repository.hybrid_search(
            request.query,
            analysis.language,
            analysis.category,
            limit=3,
            source_collection=request.source_collection,
        )
        trace["retrieved_chunks"] = [item.model_dump(mode="json") for item in candidates]
        trace["reranker"] = {"enabled": False, "pipeline": "hybrid_top_3_direct"}
        self._persist_trace(trace)
        evidence = candidates[:3]
        decision = (
            await self.routing_evidence.evaluate_evidence(request.query, analysis, evidence)
            if self.routing_evidence is not None
            else self.evaluator.decide(analysis, evidence)
        )
        if (
            self.routing_evidence is not None
            and decision.state == EvidenceState.INSUFFICIENT_EVIDENCE
            and analysis.needs_clarification
            and analysis.missing_facts
        ):
            clarification = self.evaluator.decide(analysis, evidence)
            if clarification.state == EvidenceState.NEEDS_CLARIFICATION:
                decision = clarification
        trace["evidence_gate"] = decision.model_dump(mode="json")
        trace["final_evidence"] = [item.model_dump(mode="json") for item in evidence[:3]]
        self._persist_trace(trace)
        if decision.state == EvidenceState.NEEDS_CLARIFICATION:
            response = AnswerResponse(state=decision.state, language=analysis.language, clarification_question=decision.clarification_question)
            return self._finish(trace, response, citation_valid=True)
        if decision.state != EvidenceState.ANSWERABLE:
            message = "هذه المسألة تحتاج إلى تفاصيل أو نظر من مختص، ولم نجد في المصادر المتاحة ما يكفي لإعطائك جوابًا موثقًا."
            response = AnswerResponse(state=decision.state, language=analysis.language, escalation_message=message)
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
            )
            return self._finish(trace, response, citation_valid=True)
        allowed = {item.chunk_id: item for item in evidence if item.chunk_id}
        expected_urls = [allowed[chunk_id].source_url for chunk_id in generated.citation_chunk_ids if chunk_id in allowed]
        citation_valid = (
            bool(generated.citation_chunk_ids)
            and all(chunk_id in allowed for chunk_id in generated.citation_chunk_ids)
            and generated.citation_urls == expected_urls
        )
        if not citation_valid:
            logger.warning("citation_validation %s", json.dumps({
                "valid": False,
                "returned_chunk_ids": generated.citation_chunk_ids,
                "returned_urls": generated.citation_urls,
                "allowed": list(allowed),
                "expected_urls": expected_urls,
            }, ensure_ascii=False))
            response = AnswerResponse(
                state=EvidenceState.INSUFFICIENT_EVIDENCE,
                language=analysis.language,
                escalation_message="رُفضت الإجابة لأن الاستشهادات لم تطابق الأدلة المسترجعة من المصدر المعتمد.",
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
        ) for item in selected[:3]]
        logger.info("citation_validation %s", json.dumps({"valid": True, "citation_chunk_ids": generated.citation_chunk_ids, "document_ids": [item.fatwa_id for item in selected]}, ensure_ascii=False))
        response = AnswerResponse(state=EvidenceState.ANSWERABLE, language=analysis.language, summary=generated.summary, explanation=generated.explanation, citations=citations)
        return self._finish(trace, response, citation_valid=True)

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
