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


def psycopg_url(database_url: str) -> str:
    return database_url.replace("postgresql+psycopg://", "postgresql://", 1)


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.9g}" for value in values) + "]"


def _coverage(query: str, text: str) -> float:
    query_terms = set(re.findall(r"[\w\u0600-\u06ff]+", normalize_arabic_for_retrieval(query)))
    if not query_terms:
        return 0.0
    text_terms = set(re.findall(r"[\w\u0600-\u06ff]+", normalize_arabic_for_retrieval(text)))
    return len(query_terms & text_terms) / len(query_terms)


def _lexical_query(query: str) -> str:
    """Build an OR query so long natural-language questions can match partial evidence."""
    terms = list(dict.fromkeys(re.findall(r"[\w\u0600-\u06ff]+", normalize_arabic_for_retrieval(query))))
    return " | ".join(terms)


class PostgresFatwaRepository(FatwaRepository):
    def __init__(self, database_url: str, embeddings: EmbeddingProvider) -> None:
        self.database_url = psycopg_url(database_url)
        self.embeddings = embeddings

    async def hybrid_search(
        self,
        query: str,
        language: str,
        category: str | None = None,
        limit: int = 20,
        source_collection: SourceCollection = SourceCollection.OFFICIAL_HACKATHON_REFERENCE,
    ) -> list[RetrievedEvidence]:
        query_vector = (await self.embeddings.embed_queries([query]))[0]
        return await asyncio.to_thread(self._search, query, query_vector, limit, source_collection)

    def _search(self, query: str, query_vector: list[float], limit: int, source_collection: SourceCollection) -> list[RetrievedEvidence]:
        sql = """
        WITH dense AS (
          SELECT c.id AS chunk_id, row_number() OVER (ORDER BY e.embedding <=> %(embedding)s::vector) AS dense_rank,
                 1 - (e.embedding <=> %(embedding)s::vector) AS dense_score
          FROM embeddings e
          JOIN fatwa_chunks c ON c.id = e.chunk_id
          JOIN fatwas f ON f.id = c.fatwa_id
          WHERE f.source_collection = %(collection)s
          ORDER BY e.embedding <=> %(embedding)s::vector
          LIMIT %(candidate_limit)s
        ), lexical AS (
          SELECT c.id AS chunk_id,
                 row_number() OVER (ORDER BY ts_rank_cd(to_tsvector('simple', c.content), to_tsquery('simple', %(lexical_query)s)) DESC) AS lexical_rank,
                 ts_rank_cd(to_tsvector('simple', c.content), to_tsquery('simple', %(lexical_query)s)) AS lexical_score
          FROM fatwa_chunks c
          JOIN fatwas f ON f.id = c.fatwa_id
          WHERE f.source_collection = %(collection)s
            AND to_tsvector('simple', c.content) @@ to_tsquery('simple', %(lexical_query)s)
          ORDER BY lexical_score DESC
          LIMIT %(candidate_limit)s
        ), fused AS (
          SELECT COALESCE(d.chunk_id, l.chunk_id) AS chunk_id,
                 d.dense_rank, d.dense_score, l.lexical_rank, l.lexical_score,
                 COALESCE(1.0 / (60 + d.dense_rank), 0) + COALESCE(1.0 / (60 + l.lexical_rank), 0) AS fused_score
          FROM dense d FULL OUTER JOIN lexical l ON l.chunk_id = d.chunk_id
        ), ranked AS (
          SELECT *, row_number() OVER (ORDER BY fused_score DESC) AS fused_rank
          FROM fused
        )
        SELECT r.chunk_id::text, f.external_id, c.title, c.content, c.source_url,
               r.dense_score, r.dense_rank, r.lexical_score, r.lexical_rank, r.fused_score, r.fused_rank,
               c.category_path, f.source_collection_name, f.source_authority, f.scholar,
               f.madhhabs, f.original_reference, f.source_type
        FROM ranked r
        JOIN fatwa_chunks c ON c.id = r.chunk_id
        JOIN fatwas f ON f.id = c.fatwa_id
        ORDER BY r.fused_rank
        LIMIT %(limit)s
        """
        params = {
            "embedding": _vector_literal(query_vector),
            "collection": source_collection.value,
            "lexical_query": _lexical_query(query),
            "candidate_limit": max(limit, 20),
            "limit": limit,
        }
        with psycopg.connect(self.database_url) as connection, connection.cursor() as cursor:
            cursor.execute(sql, params)
            rows = cursor.fetchall()
        max_fused = max((float(row[9]) for row in rows), default=1.0)
        results: list[RetrievedEvidence] = []
        for row in rows:
            content = row[3]
            references = row[16] if isinstance(row[16], list) else json.loads(row[16] or "[]")
            results.append(
                RetrievedEvidence(
                    chunk_id=row[0],
                    fatwa_id=row[1],
                    title=row[2],
                    excerpt=content,
                    source_url=row[4],
                    retrieval_score=min(1.0, float(row[9]) / max_fused if max_fused else 0.0),
                    reranker_score=0.0,
                    coverage=_coverage(query, content),
                    dense_score=float(row[5]) if row[5] is not None else None,
                    dense_rank=int(row[6]) if row[6] is not None else None,
                    lexical_score=float(row[7]) if row[7] is not None else None,
                    lexical_rank=int(row[8]) if row[8] is not None else None,
                    fused_score=float(row[9]),
                    fused_rank=int(row[10]),
                    category_path=row[11] or [],
                    source_collection=source_collection,
                    source_collection_name=row[12],
                    source_authority=row[13],
                    scholar=row[14],
                    madhhabs=row[15] or [],
                    original_reference=[SourceReference.model_validate(item) for item in references],
                    source_type=row[17],
                    conflicting_positions="اختلف العلماء" in content or "قولان" in content,
                )
            )
        logger.info("hybrid_retrieval %s", json.dumps({
            "query": query,
            "candidate_count": len(results),
            "top": [{"chunk_id": item.chunk_id, "document_id": item.fatwa_id, "dense_score": item.dense_score, "lexical_score": item.lexical_score, "fused_score": item.fused_score} for item in results[:5]],
        }, ensure_ascii=False))
        return results
