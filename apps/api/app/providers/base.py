from abc import ABC, abstractmethod
from dataclasses import dataclass
from app.models.domain import EvidenceState, GroundedGeneration, RetrievedEvidence


class SpeechToTextProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, language_hint: str | None = None) -> tuple[str, str]: ...


class TextToSpeechProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str, language: str, voice: str | None = None) -> bytes: ...


class EmbeddingProvider(ABC):
    dimensions: int

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]: ...

    async def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return await self.embed(texts)

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return await self.embed(texts)


class RerankerProvider(ABC):
    @abstractmethod
    async def rerank(self, query: str, candidates: list[RetrievedEvidence]) -> list[RetrievedEvidence]: ...


class GenerationProvider(ABC):
    @abstractmethod
    async def grounded_summary(self, query: str, evidence: list[RetrievedEvidence], language: str) -> GroundedGeneration: ...


class MockSpeechToTextProvider(SpeechToTextProvider):
    async def transcribe(self, audio: bytes, language_hint: str | None = None) -> tuple[str, str]:
        return "أنا مسافر وسأقيم أربعة أيام، هل أقصر الصلاة؟", language_hint or "ar"


class MockTextToSpeechProvider(TextToSpeechProvider):
    async def synthesize(self, text: str, language: str, voice: str | None = None) -> bytes:
        return f"MOCK_AUDIO:{language}:{text}".encode()


class MockEmbeddingProvider(EmbeddingProvider):
    dimensions = 8

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return [[((sum(map(ord, text)) + index * 31) % 997) / 997 for index in range(self.dimensions)] for text in texts]


class MockRerankerProvider(RerankerProvider):
    async def rerank(self, query: str, candidates: list[RetrievedEvidence]) -> list[RetrievedEvidence]:
        return sorted(candidates, key=lambda item: (item.reranker_score, item.coverage, item.retrieval_score), reverse=True)


class MockGenerationProvider(GenerationProvider):
    async def grounded_summary(self, query: str, evidence: list[RetrievedEvidence], language: str) -> GroundedGeneration:
        lead = evidence[0]
        if language == "en":
            return GroundedGeneration(state=EvidenceState.ANSWERABLE, summary=f"According to the approved source entry “{lead.title}”, the retrieved evidence directly addresses this question.", explanation="This is a grounded explanation; review the original Arabic source below.", citation_chunk_ids=[lead.chunk_id] if lead.chunk_id else [])
        return GroundedGeneration(state=EvidenceState.ANSWERABLE, summary=f"بحسب مادة «{lead.title}» في المرجع المعتمد، يعالج النص المسترجع هذه المسألة مباشرة.", explanation="هذا شرح موجز مبني على المصدر، ويمكن مراجعة النص العربي الأصلي أدناه.", citation_chunk_ids=[lead.chunk_id] if lead.chunk_id else [])
