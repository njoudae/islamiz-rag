import re
from pathlib import Path

import pytest

from app.ingestion.adapters import HackathonApprovedSourceAdapter
from app.models.domain import (
    AskRequest,
    EvidenceState,
    QueryAnalysis,
    RetrievedEvidence,
    SourceCollection,
)
from app.providers.base import (
    MockGenerationProvider,
    MockRerankerProvider,
    MockSpeechToTextProvider,
    MockTextToSpeechProvider,
)
from app.rag.chunking import structure_aware_chunks
from app.rag.evidence import EvidenceSufficiencyEvaluator
from app.repositories.base import DemoFatwaRepository, EmptyContactRepository
from app.services.answers import AnswerService
from app.speech.service import SpeechService


FIXTURES = Path(__file__).parent / "fixtures"
REPOSITORY_ROOT = Path(__file__).parents[3]


def _service() -> AnswerService:
    return AnswerService(DemoFatwaRepository(), MockRerankerProvider(), MockGenerationProvider())


def _evidence(**overrides) -> RetrievedEvidence:
    values = {
        "fatwa_id": 900001,
        "title": "مادة اختبار تركيبية",
        "excerpt": "نص اختباري تركيبي يحاكي مادة المصدر دون نقل corpus حقيقي.",
        "source_url": "https://dorar.net/feqhia/900001/test",
        "retrieval_score": 0.92,
        "reranker_score": 0.91,
        "coverage": 0.89,
    }
    values.update(overrides)
    return RetrievedEvidence(**values)


@pytest.mark.asyncio
async def test_answerable_requires_source():
    response = await _service().answer(AskRequest(query="أنا مسافر وسأقيم أربعة أيام، هل أقصر الصلاة؟"))
    assert response.state == EvidenceState.ANSWERABLE
    assert response.summary
    assert response.citations


@pytest.mark.asyncio
async def test_no_source_no_answer():
    response = await _service().answer(AskRequest(query="ما حكم مسألة فقهية اصطناعية غير موجودة؟"))
    assert response.state == EvidenceState.INSUFFICIENT_EVIDENCE
    assert response.summary is None
    assert response.citations == []


def test_canonical_source_preserved():
    html = (FIXTURES / "dorar_synthetic_01.html").read_text(encoding="utf-8")
    document = HackathonApprovedSourceAdapter().parse(html, "https://dorar.net/feqhia/900001/?tracking=test")
    assert document.canonical_url == "https://dorar.net/feqhia/900001/synthetic-entry-one"
    assert "?" not in document.canonical_url
    assert document.source_url.endswith("?tracking=test")


@pytest.mark.asyncio
async def test_missing_context_requests_clarification():
    response = await _service().answer(AskRequest(query="أنا مسافر، هل أقصر الصلاة؟"))
    assert response.state == EvidenceState.NEEDS_CLARIFICATION
    assert "كم تنوي الإقامة" in (response.clarification_question or "")
    assert response.summary is None


@pytest.mark.asyncio
async def test_insufficient_evidence_escalates():
    response = await _service().answer(AskRequest(query="ما حكم زكاة حالة تركيبية لا يغطيها المرجع التجريبي؟"))
    assert response.state == EvidenceState.INSUFFICIENT_EVIDENCE
    assert response.escalation_message
    assert not response.citations


@pytest.mark.asyncio
async def test_complex_case_does_not_generate_definitive_ruling():
    response = await _service().answer(AskRequest(query="لدي مسألة ميراث شخصية متشعبة، ما الحكم النهائي؟"))
    assert response.state == EvidenceState.COMPLEX_CASE
    assert response.summary is None
    assert response.citations == []
    assert response.escalation_message


def test_conflicting_evidence_is_not_merged():
    evidence = [_evidence(conflicting_positions=True), _evidence(fatwa_id=900002)]
    decision = EvidenceSufficiencyEvaluator().decide(QueryAnalysis(), evidence)
    assert decision.state == EvidenceState.CONFLICTING_EVIDENCE


@pytest.mark.asyncio
async def test_out_of_scope_does_not_generate_fatwa():
    response = await _service().answer(AskRequest(query="ما حالة الطقس غدًا في الرياض؟"))
    assert response.state == EvidenceState.OUT_OF_SCOPE
    assert response.summary is None
    assert response.citations == []


def test_original_source_text_is_preserved():
    html = (FIXTURES / "dorar_synthetic_03.html").read_text(encoding="utf-8")
    document = HackathonApprovedSourceAdapter().parse(html, "https://dorar.net/feqhia/900003/")
    assert document.answer in document.full_original_text
    assert document.full_original_text.startswith(document.title)
    assert document.original_metadata["parser"] == "dorar-feqhia-v1"


def test_retrieved_chunk_retains_source_identity():
    html = (FIXTURES / "dorar_synthetic_03.html").read_text(encoding="utf-8")
    document = HackathonApprovedSourceAdapter().parse(html, "https://dorar.net/feqhia/900003/")
    chunks = structure_aware_chunks(document, max_chars=300)
    assert chunks
    assert all(chunk.source_collection == SourceCollection.OFFICIAL_HACKATHON_REFERENCE for chunk in chunks)
    assert all(chunk.source_url == document.canonical_url for chunk in chunks)
    assert all(chunk.source_authority == document.source_authority for chunk in chunks)


@pytest.mark.asyncio
async def test_unverified_contact_is_not_displayed():
    contacts = await EmptyContactRepository().verified_contacts()
    assert contacts == []


def test_no_secret_in_public_configuration():
    env_example = (REPOSITORY_ROOT / ".env.example").read_text(encoding="utf-8")
    gitignore = (REPOSITORY_ROOT / ".gitignore").read_text(encoding="utf-8")
    forbidden = re.compile(r"(?:sk-[A-Za-z0-9_-]{20,}|ghp_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})")
    assert not forbidden.search(env_example)
    assert "CHANGE_ME_LOCAL_ONLY" in env_example
    assert ".env\n" in gitignore.replace("\r\n", "\n")
    assert "!.env.example" in gitignore


@pytest.mark.asyncio
async def test_cross_language_retrieval():
    response = await _service().answer(AskRequest(query="I am traveling for 4 days. May I shorten the prayer?"))
    assert response.state == EvidenceState.ANSWERABLE
    assert response.language == "en"
    assert response.summary and response.summary.startswith("According to")
    assert response.citations[0].source_url.host == "dorar.net"


@pytest.mark.asyncio
async def test_voice_provider_contract():
    speech = SpeechService(
        MockSpeechToTextProvider(),
        {"ar": MockTextToSpeechProvider(), "default": MockTextToSpeechProvider()},
    )
    transcript, language = await speech.transcribe(b"synthetic-audio-bytes", "ar")
    audio = await speech.synthesize(transcript, language)
    assert transcript
    assert language == "ar"
    assert audio.startswith(b"MOCK_AUDIO:ar:")
