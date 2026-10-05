"""Facts about the running service, for the website's admin area and public pages."""
from __future__ import annotations

import psycopg

from app.config import Settings
from app.repositories.postgres import psycopg_url


def service_info(settings: Settings) -> dict:
    """Model names and the real size of the knowledge base. Reads the database; calls no model."""
    with psycopg.connect(psycopg_url(settings.database_url)) as connection, connection.cursor() as cursor:
        cursor.execute("SELECT count(*) FROM fatwas")
        documents = cursor.fetchone()[0]
        cursor.execute("SELECT count(*), max(embedded_at) FROM embeddings")
        chunks, indexed_at = cursor.fetchone()
        # category_path is [book, section, sub-section, ...] as it appears in the encyclopedia.
        cursor.execute(
            """
            SELECT category_path->>0 AS book, count(DISTINCT fatwa_id) AS entries
            FROM fatwa_chunks
            WHERE jsonb_array_length(category_path) > 0
            GROUP BY 1 ORDER BY 2 DESC
            """
        )
        books = [{"title": title, "entries": entries} for title, entries in cursor.fetchall()]
        cursor.execute(
            """
            SELECT category_path->>0 AS book, COALESCE(category_path->>2, category_path->>1) AS chapter,
                   count(DISTINCT fatwa_id) AS entries
            FROM fatwa_chunks
            WHERE jsonb_array_length(category_path) > 1
            GROUP BY 1, 2 ORDER BY 3 DESC
            """
        )
        chapters = [{"book": book, "title": chapter, "entries": entries} for book, chapter, entries in cursor.fetchall()]

    return {
        "models": {
            "generation": settings.openai_generation_model,
            "embedding": settings.e5_model,
            "reranker": settings.qwen_reranker_model,
        },
        "index": {
            "documents": documents,
            "chunks": chunks,
            "indexed_at": indexed_at.isoformat() if indexed_at else None,
            "books": books,
            "chapters": chapters,
        },
    }
