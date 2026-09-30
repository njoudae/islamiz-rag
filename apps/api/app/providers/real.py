from __future__ import annotations

import asyncio
import json
import logging
import math
from typing import Literal

from pydantic import BaseModel, Field

from app.models.domain import EvidenceState, GroundedGeneration, RetrievedEvidence
from app.providers.base import EmbeddingProvider, GenerationProvider, RerankerProvider

logger = logging.getLogger("daleel.pipeline")


class E5EmbeddingProvider(EmbeddingProvider):
    """Local multilingual E5 embeddings with the model-card prefixes."""

    def __init__(self, model_name: str, device: str | None = None) -> None:
        self.model_name = model_name
        self.device = device
        self._model = None
        self.dimensions = 384

    def _load(self):
        if self._model is None:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name, device=self.device)
            self.dimensions = self._model.get_sentence_embedding_dimension()
        return self._model

    async def _encode(self, texts: list[str], prefix: Literal["query", "passage"]) -> list[list[float]]:
        def run() -> list[list[float]]:
            model = self._load()
            values = model.encode(
                [f"{prefix}: {text}" for text in texts],
                batch_size=32,
                normalize_embeddings=True,
                show_progress_bar=len(texts) > 64,
                convert_to_numpy=True,
            )
            return values.astype("float32").tolist()

        return await asyncio.to_thread(run)

    async def embed(self, texts: list[str]) -> list[list[float]]:
        return await self.embed_passages(texts)

    async def embed_queries(self, texts: list[str]) -> list[list[float]]:
        return await self._encode(texts, "query")

    async def embed_passages(self, texts: list[str]) -> list[list[float]]:
        return await self._encode(texts, "passage")


class QwenRerankerProvider(RerankerProvider):
    """Local Qwen cross-encoder reranker; no heuristic score mutation."""

    def __init__(self, model_name: str, device: str | None = None, top_k: int = 5) -> None:
        self.model_name = model_name
        self.device = device
        self.top_k = top_k
        self._model = None

    def _load(self):
        if self._model is None:
            from sentence_transformers import CrossEncoder

            self._model = CrossEncoder(
                self.model_name,
                device=self.device,
                max_length=512,
                trust_remote_code=True,
                model_kwargs={"torch_dtype": "auto"},
                processor_kwargs={"padding_side": "left"},
            )
        return self._model

    async def rerank(self, query: str, candidates: list[RetrievedEvidence]) -> list[RetrievedEvidence]:
        if not candidates:
            return []
        candidates = candidates[:5]

        def run() -> list[float]:
            raw = self._load().predict(
                [(query, item.excerpt) for item in candidates],
                batch_size=2,
                show_progress_bar=False,
            )
            flattened = raw.reshape(-1).tolist() if hasattr(raw, "reshape") else list(raw)
            return [1.0 / (1.0 + math.exp(-float(value))) for value in flattened]

        scores = await asyncio.to_thread(run)
        reranked = [item.model_copy(update={"reranker_score": score}) for item, score in zip(candidates, scores, strict=True)]
        result = sorted(reranked, key=lambda item: item.reranker_score, reverse=True)[: self.top_k]
        logger.info("qwen_rerank %s", json.dumps({"model": self.model_name, "top": [{"chunk_id": item.chunk_id, "document_id": item.fatwa_id, "score": item.reranker_score} for item in result]}, ensure_ascii=False))
        return result


class _OpenAIAnswer(BaseModel):
    state: EvidenceState
    summary: str | None = None
    explanation: str | None = None
    citation_chunk_ids: list[str] = Field(default_factory=list)
    clarification_question: str | None = None
    escalation_reason: str | None = None


class OpenAIGenerationProvider(GenerationProvider):
    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for the real text path")
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def grounded_summary(self, query: str, evidence: list[RetrievedEvidence], language: str) -> GroundedGeneration:
        evidence_payload = [
            {
                "chunk_id": item.chunk_id,
                "document_id": item.fatwa_id,
                "title": item.title,
                "text": item.excerpt,
                "canonical_url": item.source_url,
            }
            for item in evidence
        ]
        response = await self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are Daleel, a source-grounded assistant. Use only the supplied approved evidence. "
                        "Do not use general religious knowledge or web search. If evidence is insufficient, do not "
                        "provide a religious ruling. Cite only supplied chunk_id values. Answer in the requested language."
                    ),
                },
                {
                    "role": "user",
                    "content": f"language={language}\nquestion={query}\napproved_evidence={evidence_payload}",
                },
            ],
            text_format=_OpenAIAnswer,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("OpenAI returned no structured answer")
        logger.info("openai_generation %s", json.dumps({"model": self.model, "state": parsed.state.value, "citation_chunk_ids": parsed.citation_chunk_ids}, ensure_ascii=False))
        return GroundedGeneration.model_validate(parsed.model_dump())
