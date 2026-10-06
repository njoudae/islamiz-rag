"""The pipeline that serves answers: FinalRagService over the committed production index.

No model is loaded and no network call is made. Retrieval runs on the real index with a stand-in
embedder that returns a stored unit's own vector, and the two LLM steps are replaced by fixed
outputs, so each test pins down what the server itself guarantees.
"""
from __future__ import annotations

from pathlib import Path

import numpy as np
import pytest

from app.config import get_settings
from app.models.domain import AskRequest, EvidenceState
from app.services.final_rag import FinalRagService, _GroundedAnswer, _Selection

FRIDAY_PRAYER = "nav-00895"  # حكم صلاة الجمعة: a short ruling with Quran, Sunnah and ijma evidence


class UnitEmbedder:
    """Embeds any question as the stored vector of one unit, so that unit is retrieved first."""

    def __init__(self, service: FinalRagService, unit_id: str) -> None:
        self.vector = np.asarray(service.embeddings[service.unit_ids.index(unit_id)]).tolist()

    def embed_query(self, _text: str) -> list[float]:
        return self.vector


@pytest.fixture(scope="module")
def index_dir() -> Path:
    return Path(get_settings().final_index_dir)


def build(index_dir: Path, *, selection: _Selection | None = None, generated: _GroundedAnswer | None = None, **kwargs) -> FinalRagService:
    service = FinalRagService(index_dir, "", "test-model", **kwargs)
    service.query_embedder = UnitEmbedder(service, FRIDAY_PRAYER)
    if selection is not None:
        service._client = object()  # marks the generation provider as available

        async def select(_request, _candidates):
            return selection

        async def generate(_request, _selection, _units):
            return generated

        service._select = select
        service._generate = generate
    return service


def unit(service: FinalRagService, unit_id: str) -> dict:
    return service.units[service.unit_ids.index(unit_id)]


def test_the_index_is_consistent(index_dir):
    service = FinalRagService(index_dir, "", "test-model")
    assert len(service.units) == len(service.unit_ids) == service.embeddings.shape[0] == service.manifest["unit_count"]
    assert {u["book"] for u in service.units} == {"salah", "sawm"}
    assert all(u["source_url"].startswith("https://dorar.net/feqhia/") for u in service.units)


@pytest.mark.asyncio
async def test_an_answer_carries_its_source_and_the_original_evidence(index_dir):
    source = unit(build(index_dir), FRIDAY_PRAYER)
    evidence = source["authoritative_content"]["evidence"][0]
    service = build(
        index_dir,
        selection=_Selection(status="ANSWER", selected_unit_ids=[FRIDAY_PRAYER], rationale="direct"),
        generated=_GroundedAnswer(status="ANSWER", selected_unit_ids=[FRIDAY_PRAYER], answer="صلاة الجمعة فرض عين.", evidence_ids=[evidence["evidence_id"]]),
    )

    response = await service.answer(AskRequest(query="هل صلاة الجمعة فرض عين؟"))

    assert response.state == EvidenceState.ANSWERABLE
    citation = response.citations[0]
    assert str(citation.source_url) == source["source_url"]
    assert citation.excerpt == source["ruling_original"]
    assert citation.hierarchy_path[0] == source["hierarchy_original_leaf_to_root"][-1]
    # The evidence shown is the stored text, word for word; the model only named its ID.
    assert [item["text_original"] for item in citation.evidence] == [evidence["text_original"]]
    assert response.related[0].fatwa_id == source["source_id"]
    assert response.evidence_score is not None and response.model == "test-model"


@pytest.mark.asyncio
async def test_an_invented_evidence_id_is_refused(index_dir):
    service = build(
        index_dir,
        selection=_Selection(status="ANSWER", selected_unit_ids=[FRIDAY_PRAYER], rationale="direct"),
        generated=_GroundedAnswer(status="ANSWER", selected_unit_ids=[FRIDAY_PRAYER], answer="جواب", evidence_ids=["ev-does-not-exist"]),
    )

    response = await service.answer(AskRequest(query="هل صلاة الجمعة فرض عين؟"))

    assert response.state == EvidenceState.INSUFFICIENT_EVIDENCE
    assert response.summary is None and response.citations == []


@pytest.mark.asyncio
async def test_an_answer_citing_a_unit_that_was_not_selected_is_refused(index_dir):
    service = build(
        index_dir,
        selection=_Selection(status="ANSWER", selected_unit_ids=[FRIDAY_PRAYER], rationale="direct"),
        generated=_GroundedAnswer(status="ANSWER", selected_unit_ids=["nav-01550"], answer="جواب", evidence_ids=[]),
    )

    response = await service.answer(AskRequest(query="هل صلاة الجمعة فرض عين؟"))

    assert response.state == EvidenceState.INSUFFICIENT_EVIDENCE
    assert response.citations == []


@pytest.mark.asyncio
async def test_a_unit_outside_the_retrieved_five_cannot_be_selected(index_dir):
    service = build(
        index_dir,
        selection=_Selection(status="ANSWER", selected_unit_ids=["nav-does-not-exist"], rationale="invented"),
        generated=_GroundedAnswer(status="ANSWER", selected_unit_ids=[], answer="جواب بلا مصدر", evidence_ids=[]),
    )

    response = await service.answer(AskRequest(query="هل صلاة الجمعة فرض عين؟"))

    # With nothing validly selected there is nothing to cite, so there is no answer.
    assert response.state == EvidenceState.INSUFFICIENT_EVIDENCE
    assert response.summary is None and response.citations == []


@pytest.mark.asyncio
async def test_without_a_generation_provider_there_is_no_answer(index_dir):
    response = await build(index_dir).answer(AskRequest(query="هل صلاة الجمعة فرض عين؟"))

    assert response.state == EvidenceState.INSUFFICIENT_EVIDENCE
    assert response.summary is None and response.citations == []


@pytest.mark.asyncio
async def test_a_missing_fact_becomes_one_clarifying_question(index_dir):
    service = build(
        index_dir,
        selection=_Selection(status="CLARIFY", clarification_question="ما سبب الجمع؟", rationale="depends on the reason"),
        generated=_GroundedAnswer(status="CLARIFY", clarification_question="ما سبب الجمع؟"),
    )

    response = await service.answer(AskRequest(query="هل أجمع بين الصلاتين؟"))

    assert response.state == EvidenceState.NEEDS_CLARIFICATION
    assert response.clarification_question == "ما سبب الجمع؟"
    assert response.summary is None and response.citations == []


@pytest.mark.asyncio
async def test_a_personal_case_is_referred_with_a_neutral_message(index_dir):
    service = build(
        index_dir,
        selection=_Selection(status="ESCALATE", rationale="personal"),
        generated=_GroundedAnswer(status="ESCALATE", answer="نصيحة لا يجب أن تظهر"),
    )

    response = await service.answer(AskRequest(query="حلفت بالطلاق ثم حنثت، هل وقع؟"))

    assert response.state == EvidenceState.COMPLEX_CASE
    assert response.summary is None and response.citations == []
    assert "نصيحة" not in (response.escalation_message or "")


def test_illness_and_fasting_asks_whether_recovery_is_expected(index_dir):
    service = FinalRagService(index_dir, "", "test-model")
    both_branches = [(unit(service, "nav-01520"), 0.7), (unit(service, "nav-01521"), 0.69)]

    assert FinalRagService._required_clarification("أنا مريض وأفطرت في رمضان", both_branches)
    # Already said: no question. Only one branch retrieved: no question.
    assert FinalRagService._required_clarification("مرضي مزمن وأفطرت في رمضان", both_branches) is None
    assert FinalRagService._required_clarification("أنا مريض وأفطرت في رمضان", both_branches[:1]) is None


@pytest.mark.asyncio
async def test_the_optional_reranker_reorders_and_fails_safe(index_dir):
    plain = [u["unit_id"] for u, _score in await build(index_dir).retrieve_top("سؤال", 5)]

    class Reversed:
        def scores(self, _query, passages):
            return list(range(len(passages)))  # the last passage scores highest

    class Broken:
        def scores(self, _query, _passages):
            raise RuntimeError("service down")

    reranked = [u["unit_id"] for u, _score in await build(index_dir, reranker=Reversed(), rerank_depth=5).retrieve_top("سؤال", 5)]
    fallback = [u["unit_id"] for u, _score in await build(index_dir, reranker=Broken(), rerank_depth=5).retrieve_top("سؤال", 5)]

    assert plain[0] == FRIDAY_PRAYER
    assert reranked == list(reversed(plain))
    assert fallback == plain
