from fastapi import APIRouter, File, HTTPException, Response, UploadFile
from app.models.domain import AnswerResponse, AskRequest, AuthorityContact
from app.providers.base import MockGenerationProvider, MockRerankerProvider, MockSpeechToTextProvider, MockTextToSpeechProvider
from app.repositories.base import DemoFatwaRepository, EmptyContactRepository
from app.services.answers import AnswerService
from app.speech.service import SpeechService


router = APIRouter()
answer_service = AnswerService(DemoFatwaRepository(), MockRerankerProvider(), MockGenerationProvider())
speech_service = SpeechService(MockSpeechToTextProvider(), {"ar": MockTextToSpeechProvider(), "en": MockTextToSpeechProvider(), "default": MockTextToSpeechProvider()})
contact_repository = EmptyContactRepository()


@router.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok", "source_scope": "OFFICIAL_HACKATHON_REFERENCE:dorar.net/feqhia"}


@router.post("/v1/ask", response_model=AnswerResponse)
async def ask(payload: AskRequest) -> AnswerResponse:
    return await answer_service.answer(payload)


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
