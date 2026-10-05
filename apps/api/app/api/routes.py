from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from app.models.domain import AnswerResponse, AskRequest, AuthorityContact
from app.config import get_settings
from app.providers.base import MockSpeechToTextProvider, MockTextToSpeechProvider
from app.repositories.base import EmptyContactRepository
from app.services.final_rag import FinalRagService
from app.services.conversations import SQLiteConversationStore
from app.speech.service import SpeechService


router = APIRouter()
settings = get_settings()
openai_api_key = settings.openai_api_key.get_secret_value() if settings.openai_api_key else ""
answer_service = FinalRagService(
    Path(settings.final_index_dir),
    openai_api_key,
    settings.openai_generation_model,
    settings.retrieval_device,
)
speech_service = None
if (
    settings.app_env != "production"
    and settings.stt_provider == "mock"
    and settings.tts_provider_ar == "mock"
    and settings.tts_provider_en == "mock"
):
    speech_service = SpeechService(
        MockSpeechToTextProvider(),
        {"ar": MockTextToSpeechProvider(), "en": MockTextToSpeechProvider(), "default": MockTextToSpeechProvider()},
    )
contact_repository = EmptyContactRepository()
conversation_store = SQLiteConversationStore(Path(settings.conversation_db_path))


@router.get("/health")
async def health() -> dict[str, str]:
    return {
        "status": "ok",
        "source_scope": "DORAR_FINAL:SALAH+SAWM",
        "retrieval": "BAAI/bge-m3:D2:top5:grounded-selector",
    }


@router.post("/v1/ask", response_model=AnswerResponse)
async def ask(payload: AskRequest) -> AnswerResponse:
    conversation_id = payload.conversation_id or uuid4()
    locale = payload.language or "ar"
    existing = await conversation_store.get(conversation_id)
    await conversation_store.ensure(conversation_id, locale)
    awaiting = existing is not None and existing.status == "awaiting_clarification"
    original_question = (
        existing.original_question
        if awaiting and existing.original_question
        else payload.query
    )
    effective_payload = payload
    if awaiting:
        effective_payload = payload.model_copy(update={
            "query": (
                f"السؤال الأصلي: {original_question}\n"
                f"إجابة المستخدم عن سؤال الاستيضاح: {payload.query}"
            )
        })
    await conversation_store.add_message(
        conversation_id,
        "user",
        payload.query,
        "clarification_reply" if awaiting else "question",
    )
    response = await answer_service.answer(effective_payload)
    response = response.model_copy(update={"conversation_id": conversation_id})
    if response.state.value == "NEEDS_CLARIFICATION":
        clarification = response.clarification_question or ""
        await conversation_store.set_awaiting(
            conversation_id,
            original_question,
            clarification,
            response.runtime_context,
        )
    else:
        await conversation_store.complete(conversation_id, response.runtime_context)
    assistant_content = (
        response.summary
        or response.clarification_question
        or response.escalation_message
        or ""
    )
    await conversation_store.add_message(
        conversation_id,
        "assistant",
        assistant_content,
        response.state.value,
    )
    return response


@router.post("/v1/speech/transcribe")
async def transcribe(file: UploadFile = File(...), language: str | None = None) -> dict[str, str]:
    if speech_service is None or settings.stt_provider != "mock":
        raise HTTPException(status_code=503, detail="Speech transcription is not configured")
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio upload")
    text, detected = await speech_service.transcribe(data, language)
    return {"text": text, "language": detected}


@router.post("/v1/speech/synthesize")
async def synthesize(text: str, language: str = "ar") -> Response:
    configured = settings.tts_provider_ar if language == "ar" else settings.tts_provider_en
    if speech_service is None or configured != "mock":
        raise HTTPException(status_code=503, detail="Speech synthesis is not configured")
    audio = await speech_service.synthesize(text, language)
    return Response(content=audio, media_type="audio/mpeg", headers={"X-Synthetic-Voice": "neutral"})


@router.get("/v1/authority-contacts", response_model=list[AuthorityContact])
async def contacts(country: str | None = None) -> list[AuthorityContact]:
    # Repository contract must filter is_verified=true at query time.
    return await contact_repository.verified_contacts(country)
