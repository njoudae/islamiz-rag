"""The HTTP surface of the AI service: the internal token, the info endpoint, the scope
check and the server-side clarification state. The answer pipeline itself is replaced by fixed
responses; no model is loaded and no network call is made."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from pydantic import SecretStr

from app.api import routes
from app.main import app
from app.models.domain import AnswerResponse, Citation, EvidenceState
from app.services.conversations import SQLiteConversationStore

TOKEN = {"X-Internal-Token": "test-token"}


@pytest.fixture
def client(monkeypatch, tmp_path):
    monkeypatch.setattr(routes.settings, "internal_api_token", SecretStr("test-token"))
    monkeypatch.setattr(routes, "conversation_store", SQLiteConversationStore(tmp_path / "conversations.sqlite3"))
    return TestClient(app)


def answer_with(monkeypatch, *responses: AnswerResponse) -> list[str]:
    """Make the pipeline return the given responses in turn; collect the questions it was asked."""
    asked: list[str] = []
    queue = list(responses)

    async def answer(request):
        asked.append(request.query)
        return queue.pop(0)

    monkeypatch.setattr(routes.answer_service, "answer", answer)
    return asked


def scope(monkeypatch, out_of_scope: bool) -> None:
    async def is_out_of_scope(_query, _language):
        return out_of_scope

    monkeypatch.setattr(routes, "is_out_of_scope", is_out_of_scope)


def refusal() -> AnswerResponse:
    return AnswerResponse(state=EvidenceState.INSUFFICIENT_EVIDENCE, language="ar", escalation_message="لا تكفي المادة.")


def sourced_answer() -> AnswerResponse:
    citation = Citation(fatwa_id=1575, title="حكم صلاة الجمعة", source_url="https://dorar.net/feqhia/1575")
    return AnswerResponse(state=EvidenceState.ANSWERABLE, language="ar", summary="فرض عين.", citations=[citation])


def test_health_is_public_and_everything_else_needs_the_token(client):
    assert client.get("/health").status_code == 200
    assert client.get("/v1/info").status_code == 401
    assert client.post("/v1/ask", json={"query": "ما حكم الأذان؟"}).status_code == 401
    assert client.get("/v1/info", headers={"X-Internal-Token": "wrong"}).status_code == 401


def test_info_reports_the_loaded_index(client):
    body = client.get("/v1/info", headers=TOKEN).json()

    assert body["index"]["documents"] == body["index"]["chunks"] == 584
    assert sorted(book["entries"] for book in body["index"]["books"]) == [74, 510]  # Sawm, Salah
    assert body["models"]["embedding"] == "BAAI/bge-m3"


def test_a_refusal_for_a_non_fiqh_question_becomes_out_of_scope(client, monkeypatch):
    answer_with(monkeypatch, refusal())
    scope(monkeypatch, out_of_scope=True)

    body = client.post("/v1/ask", headers=TOKEN, json={"query": "ما حالة الطقس غدًا؟"}).json()

    assert body["state"] == "OUT_OF_SCOPE"
    assert body["summary"] is None and body["citations"] == []


def test_a_fiqh_question_the_index_cannot_answer_stays_insufficient(client, monkeypatch):
    answer_with(monkeypatch, refusal())
    scope(monkeypatch, out_of_scope=False)

    assert client.post("/v1/ask", headers=TOKEN, json={"query": "ما مقدار زكاة الذهب؟"}).json()["state"] == "INSUFFICIENT_EVIDENCE"


def test_the_scope_check_never_overrides_a_sourced_answer(client, monkeypatch):
    answer_with(monkeypatch, sourced_answer())
    scope(monkeypatch, out_of_scope=True)

    body = client.post("/v1/ask", headers=TOKEN, json={"query": "هل صلاة الجمعة فرض عين؟"}).json()

    assert body["state"] == "ANSWERABLE"
    assert body["citations"][0]["source_url"] == "https://dorar.net/feqhia/1575"


def test_a_reply_to_a_clarification_is_answered_together_with_the_original_question(client, monkeypatch):
    clarify = AnswerResponse(state=EvidenceState.NEEDS_CLARIFICATION, language="ar", clarification_question="هل مرضك يُرجى شفاؤه؟")
    asked = answer_with(monkeypatch, clarify, sourced_answer())
    scope(monkeypatch, out_of_scope=False)

    first = client.post("/v1/ask", headers=TOKEN, json={"query": "أنا مريض وأفطرت في رمضان"}).json()
    second = client.post("/v1/ask", headers=TOKEN, json={"query": "مرض مزمن", "conversation_id": first["conversation_id"]}).json()

    assert first["state"] == "NEEDS_CLARIFICATION" and first["conversation_id"]
    assert second["conversation_id"] == first["conversation_id"]
    assert "أنا مريض وأفطرت في رمضان" in asked[1] and "مرض مزمن" in asked[1]


def test_separate_conversations_share_nothing(client, monkeypatch):
    clarify = AnswerResponse(state=EvidenceState.NEEDS_CLARIFICATION, language="ar", clarification_question="؟")
    asked = answer_with(monkeypatch, clarify, refusal())
    scope(monkeypatch, out_of_scope=False)

    client.post("/v1/ask", headers=TOKEN, json={"query": "أنا مريض وأفطرت في رمضان"})
    client.post("/v1/ask", headers=TOKEN, json={"query": "ما حكم الأذان؟"})

    assert asked[1] == "ما حكم الأذان؟"
