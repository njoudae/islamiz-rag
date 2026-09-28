from app.models.domain import AnswerResponse, AskRequest, Citation, EvidenceState
from app.providers.base import GenerationProvider, RerankerProvider
from app.rag.evidence import EvidenceSufficiencyEvaluator
from app.repositories.base import FatwaRepository
from app.services.query import QueryUnderstandingService


class AnswerService:
    def __init__(self, repository: FatwaRepository, reranker: RerankerProvider, generator: GenerationProvider):
        self.repository = repository
        self.reranker = reranker
        self.generator = generator
        self.understanding = QueryUnderstandingService()
        self.evaluator = EvidenceSufficiencyEvaluator()

    async def answer(self, request: AskRequest) -> AnswerResponse:
        analysis = await self.understanding.analyze(request.query, request.language)
        candidates = await self.repository.hybrid_search(request.query, analysis.language, analysis.category, source_collection=request.source_collection)
        evidence = await self.reranker.rerank(request.query, candidates)
        decision = self.evaluator.decide(analysis, evidence)
        if decision.state == EvidenceState.NEEDS_CLARIFICATION:
            return AnswerResponse(state=decision.state, language=analysis.language, clarification_question=decision.clarification_question)
        if decision.state != EvidenceState.ANSWERABLE:
            message = "هذه المسألة تحتاج إلى تفاصيل أو نظر من مختص، ولم نجد في المصادر المتاحة ما يكفي لإعطائك جوابًا موثقًا."
            return AnswerResponse(state=decision.state, language=analysis.language, escalation_message=message)

        summary, explanation = await self.generator.grounded_summary(request.query, evidence, analysis.language)
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
        ) for item in evidence[:3]]
        return AnswerResponse(state=EvidenceState.ANSWERABLE, language=analysis.language, summary=summary, explanation=explanation, citations=citations)
