from app.providers.base import SpeechToTextProvider, TextToSpeechProvider


class SpeechService:
    def __init__(self, stt: SpeechToTextProvider, tts_by_language: dict[str, TextToSpeechProvider]):
        self.stt = stt
        self.tts_by_language = tts_by_language

    async def transcribe(self, audio: bytes, language_hint: str | None = None) -> tuple[str, str]:
        return await self.stt.transcribe(audio, language_hint)

    async def synthesize(self, text: str, language: str) -> bytes:
        provider = self.tts_by_language.get(language) or self.tts_by_language.get("default")
        if provider is None:
            raise ValueError(f"No TTS provider configured for {language}")
        return await provider.synthesize(text, language, voice="neutral")

