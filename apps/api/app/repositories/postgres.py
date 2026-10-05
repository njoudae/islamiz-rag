from __future__ import annotations

import asyncio
import json
import logging
import re
from typing import Any

import psycopg

from app.ingestion.parser import normalize_arabic_for_retrieval
from app.models.domain import RetrievedEvidence, SourceCollection, SourceReference
from app.providers.base import EmbeddingProvider
from app.repositories.base import FatwaRepository

logger = logging.getLogger("daleel.pipeline")

RRF_K = 60
DENSE_CANDIDATE_LIMIT = 20
LEXICAL_CANDIDATE_LIMIT = 20
METADATA_BOOST_WEIGHT = 0.20
_ARABIC_STOPWORDS = {
    "ما", "ماذا", "من", "في", "عن", "علي", "الي", "هل", "كيف", "متي", "اذا", "او", "و", "ثم",
    "هو", "هي", "هذا", "هذه", "ذلك", "تلك", "الذي", "التي", "حكم", "الحكم", "شرعي", "الشرعي",
}


def psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.9g}" for value in values) + "]"


def _terms(value: str) -> list[str]:
    return list(dict.fromkeys(re.findall(r"[\w\u0600-\u06ff]+", normalize_arabic_for_retrieval(value))))


def _coverage(query: str, text: str) -> float:
    query_terms = set(_terms(query))
    if not query_terms:
        return 0.0
    text_terms = set(_terms(text))
    return len(query_terms & text_terms) / len(query_terms)


def _lexical_query(query: str) -> str:
    """Build a lightly stemmed OR query for weighted Arabic lexical fields."""
    terms = [term for term in _terms(query) if term not in _ARABIC_STOPWORDS]
    if not terms:
        terms = _terms(query)
    variants: list[str] = []
    for term in terms:
        for variant in _light_arabic_variants(term):
            if variant and variant not in variants:
                variants.append(variant)
    return " | ".join(variants)


def _light_arabic_variants(term: str) -> list[str]:
    """Generate a few surface forms without a dictionary or aggressive root stemming."""
    values = [term]
    core = _metadata_term(term)
    if core != term:
        values.append(core)

    # Imperative/present-like form -> bare triliteral root and common fu'ul masdar.
    if len(core) == 4 and core.startswith("ا"):
        root = core[1:]
        values.extend((root, f"ال{root}", f"ال{root[0]}{root[1]}و{root[2]}"))

    # Common fu'ul nominal form (ركوع/سجود) -> root and verb-like form.
    if len(core) == 4 and core[2] == "و":
        root = f"{core[0]}{core[1]}{core[3]}"
        values.extend((root, f"ال{core}", f"ا{root}"))

    # Common fa'il/fa'eel-like adjective (مريض) -> bare noun (مرض).
    if len(core) == 4 and core[2] == "ي":
        root = f"{core[0]}{core[1]}{core[3]}"
        values.extend((root, f"ال{root}"))

    # Definite triliteral noun (المرض) -> a common fa'eel-like adjective (مريض).
    if term.startswith("ال") and len(core) == 3:
        values.append(f"{core[0]}{core[1]}ي{core[2]}")

    return list(dict.fromkeys(values))


def _metadata_term(term: str) -> str:
    for prefix in ("وال", "فال", "بال", "كال", "لل", "ال"):
        if term.startswith(prefix) and len(term) - len(prefix) >= 3:
            return term[len(prefix):]
    for prefix in ("و", "ف", "ب", "ك", "ل"):
        if term.startswith(prefix) and len(term) > 4:
            return term[1:]
    return term


def _metadata_match_score(query: str, candidate: dict[str, Any]) -> float:
    query_terms = {
        _metadata_term(term) for term in _terms(query) if len(term) >= 3 and term not in _ARABIC_STOPWORDS
    }
    if not query_terms:
        return 0.0
    hierarchy = candidate.get("hierarchy") or {}
    values = [
        hierarchy.get("kitab"), hierarchy.get("bab"), hierarchy.get("fasl"), hierarchy.get("mabhas"),
        hierarchy.get("matlab"), hierarchy.get("far"), hierarchy.get("position"), hierarchy.get("masala"),
        candidate.get("topic"), *(candidate.get("tags") or []),
    ]
    normalized_values = [normalize_arabic_for_retrieval(str(value)) for value in values if value]
    metadata_terms = {_metadata_term(term) for value in normalized_values for term in _terms(value)}
    token_score = len(query_terms & metadata_terms) / len(query_terms)
    normalized_query = normalize_arabic_for_retrieval(query)
    phrase_match = any(len(value.split()) >= 2 and value in normalized_query for value in normalized_values)
    return min(1.0, token_score + (0.20 if phrase_match else 0.0))


def _rrf_fuse(query: str, dense: list[dict[str, Any]], lexical: list[dict[str, Any]]) -> list[dict[str, Any]]:
    combined: dict[str, dict[str, Any]] = {}
    for candidate in dense:
        combined[candidate["chunk_id"]] = dict(candidate)
    for candidate in lexical:
        current = combined.setdefault(candidate["chunk_id"], dict(candidate))
        current["lexical_rank"] = candidate["lexical_rank"]
        current["lexical_score"] = candidate["lexical_score"]

    for candidate in combined.values():
        dense_rank = candidate.get("dense_rank")
        lexical_rank = candidate.get("lexical_rank")
        rrf_score = (1.0 / (RRF_K + dense_rank) if dense_rank else 0.0) + (
            1.0 / (RRF_K + lexical_rank) if lexical_rank else 0.0
        )
        metadata_score = _metadata_match_score(query, candidate)
        candidate["rrf_score"] = rrf_score
        candidate["metadata_score"] = metadata_score
        candidate["fused_score"] = rrf_score * (1.0 + METADATA_BOOST_WEIGHT * metadata_score)

    ranked = sorted(
        combined.values(),
        key=lambda item: (
            -item["fused_score"],
            -item["rrf_score"],
            -(item.get("dense_score") or 0.0),
            -(item.get("lexical_score") or 0.0),
            item["chunk_id"],
        ),
    )
    for rank, candidate in enumerate(ranked, 1):
        candidate["fused_rank"] = rank
    return ranked


class PostgresFatwaRepository(FatwaRepository):
    def __init__(self, database_url: str, embeddings: EmbeddingProvider) -> None:
        self.database_url = psycopg_url(database_url)
        self.embeddings = embeddings

    async def hybrid_search(
        self,
        query: str,
        language: str,
        category: str | None = None,
        limit: int = 10,
        source_collection: SourceCollection = SourceCollection.OFFICIAL_HACKATHON_REFERENCE,
    ) -> list[RetrievedEvidence]:
        query_vector = (await self.embeddings.embed_queries([query]))[0]
        return await self.hybrid_search_with_vector(query, query_vector, limit, source_collection)

    async def hybrid_search_with_vector(
        self,
        query: str,
        query_vector: list[float],
        limit: int = 10,
        source_collection: SourceCollection = SourceCollection.OFFICIAL_HACKATHON_REFERENCE,
    ) -> list[RetrievedEvidence]:
        dense, lexical = await asyncio.gather(
            asyncio.to_thread(self._dense_candidates, query_vector, source_collection, DENSE_CANDIDATE_LIMIT),
            asyncio.to_thread(self._lexical_candidates, query, source_collection, LEXICAL_CANDIDATE_LIMIT),
        )
        fused = _rrf_fuse(query, dense, lexical)[:limit]
        results = self._as_evidence(query, fused, source_collection, fused=True)
        logger.info("hybrid_retrieval %s", json.dumps({
            "query": query,
            "dense_candidates": len(dense),
            "lexical_candidates": len(lexical),
            "top": [{
                "chunk_id": item.chunk_id,
                "document_id": item.fatwa_id,
                "dense_rank": item.dense_rank,
                "lexical_rank": item.lexical_rank,
                "metadata_score": item.metadata_score,
                "fused_score": item.fused_score,
            } for item in results[:5]],
        }, ensure_ascii=False))
        return results

    async def dense_search_with_vector(
        self,
        query: str,
        query_vector: list[float],
        limit: int = 10,
        source_collection: SourceCollection = SourceCollection.OFFICIAL_HACKATHON_REFERENCE,
    ) -> list[RetrievedEvidence]:
        dense = await asyncio.to_thread(self._dense_candidates, query_vector, source_collection, limit)
        return self._as_evidence(query, dense, source_collection, fused=False)

    def _dense_candidates(
        self,
        query_vector: list[float],
        source_collection: SourceCollection,
        limit: int,
    ) -> list[dict[str, Any]]:
        sql = """
        SELECT c.id::text, f.external_id, c.title, c.content, c.source_url,
               1 - (e.embedding <=> %(embedding)s::vector) AS score,
               c.category_path, f.source_collection_name, f.source_authority, f.scholar,
               f.madhhabs, f.original_reference, f.source_type, c.hierarchy, c.tags, c.topic
        FROM embeddings e
        JOIN fatwa_chunks c ON c.id = e.chunk_id
        JOIN fatwas f ON f.id = c.fatwa_id
        WHERE f.source_collection = %(collection)s
        ORDER BY e.embedding <=> %(embedding)s::vector
        LIMIT %(limit)s
        """
        params = {
            "embedding": _vector_literal(query_vector),
            "collection": source_collection.value,
            "limit": limit,
        }
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return [self._candidate(row, dense_rank=rank) for rank, row in enumerate(rows, 1)]

    def _lexical_candidates(
        self,
        query: str,
        source_collection: SourceCollection,
        limit: int,
    ) -> list[dict[str, Any]]:
        lexical_query = _lexical_query(query)
        if not lexical_query:
            return []
        sql = """
        SELECT c.id::text, f.external_id, c.title, c.content, c.source_url,
               ts_rank_cd(weighted.document, query.value) AS score,
               c.category_path, f.source_collection_name, f.source_authority, f.scholar,
               f.madhhabs, f.original_reference, f.source_type, c.hierarchy, c.tags, c.topic
        FROM fatwa_chunks c
        JOIN fatwas f ON f.id = c.fatwa_id
        CROSS JOIN LATERAL (
          SELECT
            COALESCE((
              SELECT string_agg(pair->>'question', ' ')
              FROM jsonb_array_elements(COALESCE(c.qa_pairs, '[]'::jsonb)) AS pair
            ), '') AS questions,
            concat_ws(' ',
              c.title,
              c.topic,
              c.hierarchy->>'kitab',
              c.hierarchy->>'bab',
              c.hierarchy->>'fasl',
              c.hierarchy->>'mabhas',
              c.hierarchy->>'matlab',
              c.hierarchy->>'far',
              c.hierarchy->>'position',
              c.hierarchy->>'masala',
              COALESCE((
                SELECT string_agg(value, ' ')
                FROM jsonb_array_elements_text(COALESCE(c.hierarchy->'path', '[]'::jsonb)) AS value
              ), ''),
              COALESCE((
                SELECT string_agg(value, ' ')
                FROM jsonb_array_elements_text(COALESCE(c.tags, '[]'::jsonb)) AS value
              ), '')
            ) AS hierarchy_titles
        ) AS fields
        CROSS JOIN LATERAL (
          SELECT
            setweight(to_tsvector('simple', fields.questions), 'A') ||
            setweight(to_tsvector('simple', fields.hierarchy_titles), 'B') ||
            setweight(to_tsvector('simple', COALESCE(c.ruling, '')), 'C') ||
            setweight(to_tsvector('simple', COALESCE(c.retrieval_text, c.content)), 'D')
            AS document
        ) AS weighted
        CROSS JOIN LATERAL (
          SELECT to_tsquery('simple', %(lexical_query)s) AS value
        ) AS query
        WHERE f.source_collection = %(collection)s
          AND weighted.document @@ query.value
        ORDER BY score DESC, c.id
        LIMIT %(limit)s
        """
        params = {"collection": source_collection.value, "lexical_query": lexical_query, "limit": limit}
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        return [self._candidate(row, lexical_rank=rank) for rank, row in enumerate(rows, 1)]

    @staticmethod
    def _candidate(
        row: tuple[Any, ...],
        dense_rank: int | None = None,
        lexical_rank: int | None = None,
    ) -> dict[str, Any]:
        return {
            "chunk_id": row[0], "fatwa_id": row[1], "title": row[2], "content": row[3], "source_url": row[4],
            "dense_score": float(row[5]) if dense_rank is not None else None,
            "dense_rank": dense_rank,
            "lexical_score": float(row[5]) if lexical_rank is not None else None,
            "lexical_rank": lexical_rank,
            "category_path": row[6] or [], "source_collection_name": row[7], "source_authority": row[8],
            "scholar": row[9], "madhhabs": row[10] or [], "original_reference": row[11] or [],
            "source_type": row[12], "hierarchy": row[13] or {}, "tags": row[14] or [], "topic": row[15],
        }

    @staticmethod
    def _as_evidence(
        query: str,
        candidates: list[dict[str, Any]],
        source_collection: SourceCollection,
        fused: bool,
    ) -> list[RetrievedEvidence]:
        max_score = max((float(item.get("fused_score") or 0.0) for item in candidates), default=1.0)
        results: list[RetrievedEvidence] = []
        for index, item in enumerate(candidates, 1):
            references = item["original_reference"]
            if not isinstance(references, list):
                references = json.loads(references or "[]")
            dense_score = item.get("dense_score")
            normalized_score = (
                min(1.0, float(item["fused_score"]) / max_score) if fused and max_score
                else min(1.0, max(0.0, float(dense_score or 0.0)))
            )
            results.append(RetrievedEvidence(
                chunk_id=item["chunk_id"], fatwa_id=item["fatwa_id"], title=item["title"],
                excerpt=item["content"], source_url=item["source_url"], retrieval_score=normalized_score,
                reranker_score=0.0, coverage=_coverage(query, item["content"]), dense_score=dense_score,
                dense_rank=item.get("dense_rank"), lexical_score=item.get("lexical_score"),
                lexical_rank=item.get("lexical_rank"), metadata_score=item.get("metadata_score"),
                fused_score=item.get("fused_score") if fused else None, fused_rank=index if fused else None,
                category_path=item["category_path"], source_collection=source_collection,
                source_collection_name=item["source_collection_name"], source_authority=item["source_authority"],
                scholar=item["scholar"], madhhabs=item["madhhabs"],
                original_reference=[SourceReference.model_validate(reference) for reference in references],
                source_type=item["source_type"],
                conflicting_positions="اختلف العلماء" in item["content"] or "قولان" in item["content"],
            ))
        return results
