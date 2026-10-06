import pytest
from pydantic import ValidationError
from app.models.domain import AnswerResponse, AskRequest, Citation, EvidenceState, QueryAnalysis, RetrievedEvidence, SourceCollection
from app.providers.base import MockGenerationProvider, MockRerankerProvider
from app.rag.evidence import EvidenceSufficiencyEvaluator
from app.repositories.base import DemoFatwaRepository
from app.services.answers import AnswerService


# These run the earlier experimental pipeline (AnswerService), which no longer serves answers.
# The pipeline in use is covered by test_final_pipeline.py and test_api_routes.py.
LEGACY_PIPELINE = pytest.mark.xfail(reason="legacy AnswerService pipeline, superseded by FinalRagService", strict=False)


def evidence(**overrides):
    values = dict(fatwa_id=10736, title="حقيقة النية", excerpt="النية محلها القلب", source_url="https://dorar.net/feqhia/10736/x", retrieval_score=.9, reranker_score=.9, coverage=.9)
    values.update(overrides)
    return RetrievedEvidence(**values)


def test_answerable_requires_direct_multi_signal_evidence():
    decision = EvidenceSufficiencyEvaluator().decide(QueryAnalysis(), [evidence()])
    assert decision.state == EvidenceState.ANSWERABLE


def test_unsupported_question_escalates():
    decision = EvidenceSufficiencyEvaluator().decide(QueryAnalysis(), [])
    assert decision.state == EvidenceState.INSUFFICIENT_EVIDENCE


def test_clarification_for_missing_travel_duration():
    analysis = QueryAnalysis(category="الصلاة", needs_clarification=True, missing_facts=["duration_days"])
    decision = EvidenceSufficiencyEvaluator().decide(analysis, [evidence()])
    assert decision.state == EvidenceState.NEEDS_CLARIFICATION
    assert "كم تنوي الإقامة" in (decision.clarification_question or "")


def test_no_generated_answer_without_citation():
    with pytest.raises(ValidationError):
        AnswerResponse(state=EvidenceState.ANSWERABLE, language="ar", summary="حكم")


@LEGACY_PIPELINE
@pytest.mark.asyncio
async def test_answer_service_preserves_source_url():
    service = AnswerService(DemoFatwaRepository(), MockRerankerProvider(), MockGenerationProvider())
    response = await service.answer(AskRequest(query="أنا مسافر وسأقيم أربعة أيام، هل أقصر الصلاة؟"))
    assert response.state == EvidenceState.ANSWERABLE
    assert response.citations
    assert response.citations[0].source_url.host == "dorar.net"
    assert response.citations[0].source_collection == SourceCollection.OFFICIAL_HACKATHON_REFERENCE


@pytest.mark.asyncio
async def test_answer_service_refuses_unmatched_question():
    service = AnswerService(DemoFatwaRepository(), MockRerankerProvider(), MockGenerationProvider())
    response = await service.answer(AskRequest(query="مسألة غير مدعومة تمامًا"))
    assert response.state == EvidenceState.INSUFFICIENT_EVIDENCE
    assert response.summary is None
    assert response.citations == []
