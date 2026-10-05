import asyncio
import secrets

from fastapi import APIRouter, Depends, File, HTTPException, Response, Security, UploadFile, status
from fastapi.security import APIKeyHeader
from app.models.domain import AnswerResponse, AskRequest, AuthorityContact
from app.config import get_settings
from app.providers.base import MockSpeechToTextProvider, MockTextToSpeechProvider
from app.providers.real import E5EmbeddingProvider, OpenAIGenerationProvider, QwenRerankerProvider
from app.repositories.base import EmptyContactRepository
from app.repositories.postgres import PostgresFatwaRepository
from app.services.answers import AnswerService
from app.services.info import service_info
from app.speech.service import SpeechService


settings = get_settings()
internal_token_header = APIKeyHeader(name="X-Internal-Token", auto_error=False, description="Shared secret sent by the website backend")


def require_internal_token(token: str | None = Security(internal_token_header)) -> None:
    """Restrict /v1 to the website backend when INTERNAL_API_TOKEN is configured."""
    expected = settings.internal_api_token.get_secret_value() if settings.internal_api_token else ""
    if not expected:
        return
    if not token or not secrets.compare_digest(token.encode(), expected.encode()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or missing internal token")


public_router = APIRouter()
router = APIRouter(dependencies=[Depends(require_internal_token)])
embedding_provider = E5EmbeddingProvider(settings.e5_model)
answer_service = AnswerService(
    PostgresFatwaRepository(settings.database_url, embedding_provider),
    QwenRerankerProvider(settings.qwen_reranker_model, device="cpu", top_k=5),
    OpenAIGenerationProvider(
        settings.openai_api_key.get_secret_value() if settings.openai_api_key else "",
        settings.openai_generation_model,
    ),
    persist_runtime_artifacts=True,
)
speech_service = SpeechService(MockSpeechToTextProvider(), {"ar": MockTextToSpeechProvider(), "en": MockTextToSpeechProvider(), "default": MockTextToSpeechProvider()})
contact_repository = EmptyContactRepository()


@public_router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "source_scope": "OFFICIAL_HACKATHON_REFERENCE:dorar.net/feqhia"}


@router.post("/v1/ask", response_model=AnswerResponse)
async def ask(payload: AskRequest) -> AnswerResponse:
    return await answer_service.answer(payload)


@router.get("/v1/info")
async def info() -> dict:
    """Model names and knowledge-base size. Reads the database only; calls no model."""
    return await asyncio.to_thread(service_info, settings)


@router.post("/v1/speech/transcribe")
async def transcribe(file: UploadFile = File(...), language: str | None = None) -> dict[str, str]:
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty audio upload")
    text, detected = await speech_service.transcribe(data, language)
    return {"text": text, "language": detected}


@router.post("/v1/speech/synthesize")
async def synthesize(text: str, language: str = "ar") -> Response:
    audio = await speech_service.synthesize(text, language)
    return Response(content=audio, media_type="audio/mpeg", headers={"X-Synthetic-Voice": "neutral"})


@router.get("/v1/authority-contacts", response_model=list[AuthorityContact])
async def contacts(country: str | None = None) -> list[AuthorityContact]:
    # Repository contract must filter is_verified=true at query time.
    return await contact_repository.verified_contacts(country)
