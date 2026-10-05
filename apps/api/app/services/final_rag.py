from __future__ import annotations

import asyncio
import json
import os
import re
import unicodedata
from pathlib import Path
from typing import Any, Literal

import numpy as np
from pydantic import BaseModel, Field

from app.models.domain import AnswerResponse, AskRequest, Citation, EvidenceState, RelatedSource


ARABIC_DIACRITICS = re.compile(r"[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed]")


def normalize_arabic(value: str) -> str:
    """Must remain identical to the final benchmark normalizer."""
    value = unicodedata.normalize("NFKC", value or "")
    value = ARABIC_DIACRITICS.sub("", value).replace("ـ", "")
    value = value.translate(str.maketrans({"أ": "ا", "إ": "ا", "آ": "ا", "ى": "ي"}))
    value = "".join(" " if unicodedata.category(ch)[0] in {"P", "S"} else ch for ch in value)
    return re.sub(r"\s+", " ", value).strip()


class _Selection(BaseModel):
    status: Literal["ANSWER", "CLARIFY", "INSUFFICIENT_EVIDENCE", "ESCALATE"]
    selected_unit_ids: list[str] = Field(default_factory=list)
    clarification_question: str | None = None
    rationale: str


class _GroundedAnswer(BaseModel):
    status: Literal["ANSWER", "CLARIFY", "INSUFFICIENT_EVIDENCE", "ESCALATE"]
    selected_unit_ids: list[str] = Field(default_factory=list)
    answer: str | None = None
    clarification_question: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class FinalRagService:
    """Final Salah/Sawm retrieval, grounded candidate selection, and generation."""

    def __init__(
        self,
        index_dir: Path,
        api_key: str,
        generation_model: str,
        retrieval_device: str | None = None,
        query_embedder: Any | None = None,
    ) -> None:
        self.index_dir = index_dir
        # Optional hosted copy of the index's model; when set, no local model is loaded.
        self.query_embedder = query_embedder
        self.manifest = json.loads((index_dir / "manifest.json").read_text(encoding="utf-8"))
        self.units = [
            json.loads(line) for line in (index_dir / "units.jsonl").open(encoding="utf-8") if line.strip()
        ]
        self.unit_ids = json.loads((index_dir / "unit_ids.json").read_text(encoding="utf-8"))
        self.embeddings = np.load(index_dir / "embeddings.npy", mmap_mode="r")
        if len(self.units) != len(self.unit_ids) or self.embeddings.shape[0] != len(self.units):
            raise RuntimeError("Production index files are inconsistent")
        self.generation_model = generation_model
        self.retrieval_device = retrieval_device
        root = Path(__file__).resolve().parents[4]
        self.selector_prompt = (root / "prompts" / "selector_prompt.txt").read_text(encoding="utf-8").strip()
        self.generation_prompt = (root / "prompts" / "generation_prompt.txt").read_text(encoding="utf-8").strip()
        self._embedding_model = None
        self._client = None
        if api_key:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=api_key)

    def _load_embedding_model(self):
        if self._embedding_model is None:
            from sentence_transformers import SentenceTransformer

            os.environ.setdefault("HF_HUB_OFFLINE", "1")
            os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")
            self._embedding_model = SentenceTransformer(
                self.manifest["model_name"],
                device=self.retrieval_device,
                trust_remote_code=True,
            )
            self._embedding_model.max_seq_length = min(int(self._embedding_model.max_seq_length), 1024)
        return self._embedding_model

    def _retrieve_sync(self, query: str) -> tuple[dict[str, Any], float]:
        return self._retrieve_top_sync(query, 1)[0]

    def _retrieve_top_sync(self, query: str, top_k: int = 5) -> list[tuple[dict[str, Any], float]]:
        if self.query_embedder is not None:
            vector = np.asarray(self.query_embedder.embed_query(normalize_arabic(query)), dtype="float32")
            vector = vector / np.linalg.norm(vector)
        else:
            model = self._load_embedding_model()
            vector = model.encode(
                [normalize_arabic(query)],
                batch_size=1,
                normalize_embeddings=True,
                convert_to_numpy=True,
                show_progress_bar=False,
            )[0].astype("float32")
        scores = np.asarray(self.embeddings) @ vector
        order = np.argsort(-scores, kind="stable")[:top_k]
        return [(self.units[int(index)], float(scores[int(index)])) for index in order]

    async def retrieve(self, query: str) -> tuple[dict[str, Any], float]:
        return await asyncio.to_thread(self._retrieve_sync, query)

    async def retrieve_top(self, query: str, top_k: int = 5) -> list[tuple[dict[str, Any], float]]:
        return await asyncio.to_thread(self._retrieve_top_sync, query, top_k)

    @staticmethod
    def _required_clarification(
        query: str,
        candidates: list[tuple[dict[str, Any], float]],
    ) -> str | None:
        """Apply only a distinction explicitly represented by retrieved source units."""
        normalized = normalize_arabic(query)
        illness_question = (
            re.search(r"(?:^|\s)(?:مريض|مرض)(?:\s|$)", normalized) is not None
            and any(term in normalized for term in ("رمضان", "صوم", "افطر", "الفطر"))
        )
        if not illness_question:
            return None
        explicit_duration = any(term in normalized for term in (
            "مزمن", "لا يرجي", "غير مرجو", "دائم", "مؤقت", "عارض", "يرجي شفاؤه", "يرجي بروه",
        ))
        if explicit_duration:
            return None
        candidate_ids = {unit["unit_id"] for unit, _score in candidates}
        has_both_source_branches = {"nav-01520", "nav-01521"}.issubset(candidate_ids)
        if has_both_source_branches:
            return "هل مرضك يُرجى شفاؤه أم لا يُرجى شفاؤه؟"
        return None

    @staticmethod
    def _candidate_context(unit: dict[str, Any], score: float) -> dict[str, Any]:
        evidence = unit["authoritative_content"].get("evidence", [])
        return {
            "id": unit["unit_id"],
            "clean_title": unit["title_clean"],
            "original_ruling": unit["ruling_original"],
            "short_hierarchy": list(reversed(unit["hierarchy_original_leaf_to_root"]))[-5:],
            "explicit_attributions": unit.get("metadata", {}).get("attributions", []),
            "evidence_available": "YES" if evidence else "NO",
            "evidence_types": list(dict.fromkeys(
                item.get("type", "other") for item in evidence if item.get("type")
            )),
            "evidence_count": len(evidence),
            "score": score,
        }

    @staticmethod
    def _source_context(unit: dict[str, Any]) -> dict[str, Any]:
        content = unit["authoritative_content"]
        return {
            "source_unit_id": unit["unit_id"],
            "title_original": unit["title_original"],
            "hierarchy_original_leaf_to_root": unit["hierarchy_original_leaf_to_root"],
            "ruling_original": unit["ruling_original"],
            "attributions": content.get("attributions", []),
            "consensus": content.get("consensus", []),
            "evidence": content.get("evidence", []),
            "reasoning": content.get("reasoning", []),
            "gender_applicability": unit.get("metadata", {}).get("gender_applicability", []),
            "source_url": unit["source_url"],
        }

    async def _select(
        self,
        request: AskRequest,
        candidates: list[tuple[dict[str, Any], float]],
    ) -> _Selection:
        if self._client is None:
            return _Selection(
                status="INSUFFICIENT_EVIDENCE",
                selected_unit_ids=[],
                rationale="Generation provider is unavailable.",
            )
        response = await self._client.responses.parse(
            model=self.generation_model,
            input=[
                {"role": "system", "content": self.selector_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": request.query,
                            "top_5": [self._candidate_context(unit, score) for unit, score in candidates],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            text_format=_Selection,
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI returned no structured selector output")
        return response.output_parsed

    async def _generate(
        self,
        request: AskRequest,
        selection: _Selection,
        units: list[dict[str, Any]],
    ) -> _GroundedAnswer:
        if self._client is None:
            return _GroundedAnswer(
                status="INSUFFICIENT_EVIDENCE",
                selected_unit_ids=[],
                evidence_ids=[],
            )
        language = request.language or ("ar" if re.search(r"[\u0600-\u06ff]", request.query) else "en")
        contexts = [self._source_context(unit) for unit in units]
        response = await self._client.responses.parse(
            model=self.generation_model,
            input=[
                {"role": "system", "content": self.generation_prompt},
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "question": request.query,
                            "selected_language": language,
                            "madhhab_preference": request.madhhab,
                            "gender_preference": request.gender,
                            "selector_status": selection.status,
                            "selector_clarification_question": selection.clarification_question,
                            "selected_unit_ids": selection.selected_unit_ids,
                            "FULL_SELECTED_SOURCE_CONTEXT": contexts,
                            "official_ifta_contacts": [],
                        },
                        ensure_ascii=False,
                    ),
                },
            ],
            text_format=_GroundedAnswer,
        )
        if response.output_parsed is None:
            raise RuntimeError("OpenAI returned no structured grounded answer")
        return response.output_parsed

    def _diagnostics(
        self,
        candidates: list[tuple[dict[str, Any], float]],
        reasons: list[str | None],
    ) -> dict[str, Any]:
        """What retrieval looked at, for the website's admin area. Never part of the answer."""
        scored = [(unit, max(0.0, min(1.0, score))) for unit, score in candidates]
        return {
            "related": [
                RelatedSource(
                    fatwa_id=int(unit["source_id"] or 0),
                    title=unit["title_original"],
                    source_url=unit["source_url"],
                    hierarchy_path=list(reversed(unit["hierarchy_original_leaf_to_root"])),
                    score=score,
                )
                for unit, score in scored[:3]
            ],
            "evidence_score": max((score for _unit, score in scored), default=None),
            "reasons": [reason for reason in reasons if reason],
            "model": self.generation_model if self._client is not None else None,
        }

    async def answer(self, request: AskRequest) -> AnswerResponse:
        candidates = await self.retrieve_top(request.query, 5)
        required_clarification = self._required_clarification(request.query, candidates)
        if required_clarification:
            return AnswerResponse(
                state=EvidenceState.NEEDS_CLARIFICATION,
                language=request.language or "ar",
                clarification_question=required_clarification,
                **self._diagnostics(candidates, ["clarification required by the retrieved source branches"]),
                runtime_context={
                    "candidate_unit_ids": [unit["unit_id"] for unit, _score in candidates],
                    "selected_unit_ids": [],
                    "internal_status": "CLARIFY",
                    "clarification_basis": "retrieved_source_branches",
                },
            )
        selection = await self._select(request, candidates)
        candidate_by_id = {unit["unit_id"]: unit for unit, _score in candidates}
        selected_ids = [
            unit_id for unit_id in selection.selected_unit_ids
            if unit_id in candidate_by_id
        ]
        selected_units = [candidate_by_id[unit_id] for unit_id in selected_ids]
        generated = await self._generate(request, selection, selected_units)
        language = request.language or ("ar" if re.search(r"[\u0600-\u06ff]", request.query) else "en")
        runtime_context = {
            "candidate_unit_ids": [unit["unit_id"] for unit, _score in candidates],
            "selector_status": selection.status,
            "selected_unit_ids": selected_ids,
            "internal_status": generated.status,
        }
        diagnostics = self._diagnostics(
            candidates,
            [f"selector: {selection.status}", selection.rationale, f"generation: {generated.status}"],
        )
        available_evidence_ids = {
            item["evidence_id"]
            for unit in selected_units
            for item in unit["authoritative_content"].get("evidence", [])
            if item.get("evidence_id")
        }
        grounded = (
            set(generated.selected_unit_ids).issubset(selected_ids)
            and set(generated.evidence_ids).issubset(available_evidence_ids)
        )
        if generated.status == "CLARIFY":
            return AnswerResponse(
                state=EvidenceState.NEEDS_CLARIFICATION,
                language=language,
                clarification_question=generated.clarification_question,
                runtime_context=runtime_context,
                **diagnostics,
            )
        if generated.status == "ESCALATE":
            neutral = (
                "The available material is insufficient for a personalized ruling. "
                "Please refer the case to an appropriate qualified authority."
                if language == "en"
                else "المادة المتاحة لا تكفي لإصدار حكم شخصي لهذه الحالة؛ تُحال المسألة إلى جهة مؤهلة مختصة."
            )
            return AnswerResponse(
                state=EvidenceState.COMPLEX_CASE,
                language=language,
                escalation_message=neutral,
                runtime_context=runtime_context,
                **diagnostics,
            )
        if generated.status != "ANSWER" or not grounded or not (generated.answer or "").strip():
            return AnswerResponse(
                state=EvidenceState.INSUFFICIENT_EVIDENCE,
                language=language,
                escalation_message="المادة المختارة لا تكفي للإجابة عن هذا السؤال دون تخمين.",
                runtime_context=runtime_context,
                **diagnostics,
            )
        citations = []
        for unit in selected_units:
            content = unit["authoritative_content"]
            attributions = content.get("attributions", [])
            madhhabs = list(dict.fromkeys(
                item["entity_original"] for item in attributions
                if item.get("entity_type") == "madhhab" and item.get("entity_original")
            ))
            scholars = [
                item["entity_original"] for item in attributions
                if item.get("entity_type") == "scholar" and item.get("entity_original")
            ]
            evidence = [
                item for item in content.get("evidence", [])
                if item.get("evidence_id") in generated.evidence_ids
            ]
            citations.append(Citation(
                fatwa_id=int(unit["source_id"] or 0),
                title=unit["title_original"],
                source_url=unit["source_url"],
                excerpt=unit["ruling_original"],
                source_authority="مؤسسة الدرر السنية",
                scholar=scholars[0] if scholars else None,
                madhhabs=madhhabs,
                hierarchy_path=list(reversed(unit["hierarchy_original_leaf_to_root"])),
                attributions=attributions,
                consensus=content.get("consensus", []),
                evidence=evidence,
            ))
        return AnswerResponse(
            state=EvidenceState.ANSWERABLE,
            language=language,
            summary=generated.answer,
            explanation=f"الوحدات المختارة: {', '.join(selected_ids)}",
            citations=citations,
            runtime_context=runtime_context,
            **diagnostics,
        )
