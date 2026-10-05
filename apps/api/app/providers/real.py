from __future__ import annotations

import asyncio
import json
import logging
import math
from typing import Literal

from pydantic import BaseModel, Field

from app.models.domain import EvidenceDecision, EvidenceState, GroundedGeneration, QueryAnalysis, RetrievedEvidence
from app.providers.base import EmbeddingProvider, GenerationProvider, RerankerProvider, RoutingEvidenceProvider

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

    def __init__(self, model_name: str, device: str | None = None, top_k: int = 10) -> None:
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
        candidates = candidates[: self.top_k]

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
        result = sorted(reranked, key=lambda item: item.reranker_score, reverse=True)
        logger.info("qwen_rerank %s", json.dumps({"model": self.model_name, "top": [{"chunk_id": item.chunk_id, "document_id": item.fatwa_id, "score": item.reranker_score} for item in result]}, ensure_ascii=False))
        return result


class _OpenAIAnswer(BaseModel):
    state: EvidenceState
    summary: str | None = None
    explanation: str | None = None
    citation_chunk_ids: list[str] = Field(default_factory=list)
    citation_urls: list[str] = Field(default_factory=list)
    clarification_question: str | None = None
    escalation_reason: str | None = None


class _OpenAIScopeDecision(BaseModel):
    classification: Literal["FIQH", "NON_FIQH"]


class _OpenAIEvidenceDecision(BaseModel):
    state: Literal["ANSWERABLE", "NEEDS_CLARIFICATION", "OUT_OF_CORPUS", "CONFLICTING_EVIDENCE"]
    reason: str
    clarification_question: str | None = None
    direct_chunk_ids: list[str] = Field(default_factory=list)


class OpenAIRoutingEvidenceProvider(RoutingEvidenceProvider):
    """GPT routing before retrieval and a text-grounded evidence sufficiency gate."""

    def __init__(self, api_key: str, model: str) -> None:
        if not api_key:
            raise ValueError("OPENAI_API_KEY is required for GPT routing and evidence decisions")
        from openai import AsyncOpenAI

        self.client = AsyncOpenAI(api_key=api_key)
        self.model = model

    async def classify_scope(self, query: str, language: str | None = None) -> str:
        response = await self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "Classify only whether the user's request is an Islamic fiqh question. "
                        "FIQH means a question seeking a practical Islamic ruling or worship guidance, "
                        "including informal Saudi Arabic. NON_FIQH includes weather, sports, programming, "
                        "finance prices, restaurants, general knowledge, and ordinary non-religious requests. "
                        "Return only the structured classification."
                    ),
                },
                {"role": "user", "content": f"language={language or 'unknown'}\nquery={query}"},
            ],
            text_format=_OpenAIScopeDecision,
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI returned no scope classification")
        return response.output_parsed.classification

    async def evaluate_evidence(
        self,
        query: str,
        analysis: QueryAnalysis,
        evidence: list[RetrievedEvidence],
    ) -> EvidenceDecision:
        payload = [
            {
                "chunk_id": item.chunk_id,
                "document_id": item.fatwa_id,
                "title": item.title,
                "text": item.excerpt,
            }
            for item in evidence
        ]
        response = await self.client.responses.parse(
            model=self.model,
            input=[
                {
                    "role": "system",
                    "content": (
                        "You are the evidence-sufficiency gate for a source-grounded fiqh assistant. "
                        "Judge the actual supplied chunk text, not document IDs, retrieval scores, titles alone, "
                        "or general religious knowledge. Return ANSWERABLE only when at least one supplied chunk "
                        "directly supports an answer to the user's requested ruling. Return NEEDS_CLARIFICATION "
                        "only when supplied evidence is relevant and a specific missing user fact materially changes "
                        "the ruling. If the evidence directly resolves the part actually asked, return ANSWERABLE "
                        "and do not request unrelated travel distance, duration, madhhab, or other details. Return "
                        "OUT_OF_CORPUS when the chunks do not address the requested fiqh issue. Return "
                        "CONFLICTING_EVIDENCE only when two or more chunks directly answer the same requested issue "
                        "with materially incompatible rulings; never infer conflict from irrelevant chunks or from "
                        "the mere presence of words such as disagreement or two opinions. For ANSWERABLE, list only "
                        "the chunk IDs that directly support the answer. For NEEDS_CLARIFICATION, ask one concise "
                        "Arabic question for the material missing fact."
                    ),
                },
                {
                    "role": "user",
                    "content": (
                        f"question={query}\n"
                        f"pre_retrieval_missing_facts={analysis.missing_facts}\n"
                        f"top_3_evidence={payload}"
                    ),
                },
            ],
            text_format=_OpenAIEvidenceDecision,
        )
        parsed = response.output_parsed
        if parsed is None:
            raise RuntimeError("OpenAI returned no evidence decision")
        state = {
            "ANSWERABLE": EvidenceState.ANSWERABLE,
            "NEEDS_CLARIFICATION": EvidenceState.NEEDS_CLARIFICATION,
            "OUT_OF_CORPUS": EvidenceState.INSUFFICIENT_EVIDENCE,
            "CONFLICTING_EVIDENCE": EvidenceState.CONFLICTING_EVIDENCE,
        }[parsed.state]
        return EvidenceDecision(
            state=state,
            reasons=[parsed.reason, *(f"direct_chunk:{chunk_id}" for chunk_id in parsed.direct_chunk_ids)],
            clarification_question=parsed.clarification_question if state == EvidenceState.NEEDS_CLARIFICATION else None,
        )


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
                        "Do not use general religious knowledge or web search. Every religious or factual claim must be "
                        "directly supported by the supplied evidence text. If evidence is insufficient, do not provide "
                        "a religious ruling. Cite only supplied chunk_id values. For citation_urls, copy the canonical_url "
                        "for each cited chunk exactly, in the same order as citation_chunk_ids. Do not invent or alter URLs. "
                        "Answer in the requested language."
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
