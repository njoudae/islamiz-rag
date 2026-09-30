from __future__ import annotations

import asyncio
import hashlib
import json
import math
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import psycopg

from app.models.domain import FatwaChunk, FatwaDocument
from app.providers.base import EmbeddingProvider
from app.rag.chunking import structure_aware_chunks
from app.repositories.postgres import psycopg_url


def stable_uuid(kind: str, identifier: str) -> uuid.UUID:
    return uuid.uuid5(uuid.NAMESPACE_URL, f"daleel:{kind}:{identifier}")


def _vector_literal(values: list[float]) -> str:
    return "[" + ",".join(f"{value:.9g}" for value in values) + "]"


async def build_real_index(
    documents_path: Path,
    artifacts_root: Path,
    database_url: str,
    embedding_provider: EmbeddingProvider,
    model_name: str,
) -> dict[str, object]:
    documents = [FatwaDocument.model_validate_json(line) for line in documents_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    chunks = [chunk for document in documents for chunk in structure_aware_chunks(document)]
    chunk_rows = [_chunk_artifact(chunk) for chunk in chunks]
    chunk_path = artifacts_root / "chunks" / "chunks.jsonl"
    chunk_path.parent.mkdir(parents=True, exist_ok=True)
    chunk_path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in chunk_rows) + "\n", encoding="utf-8")

    vectors = await embedding_provider.embed_passages([chunk.content for chunk in chunks])
    _validate_embeddings(chunks, vectors, embedding_provider.dimensions)
    embedding_dir = artifacts_root / "embeddings"
    embedding_dir.mkdir(parents=True, exist_ok=True)
    matrix = np.asarray(vectors, dtype=np.float32)
    np.save(embedding_dir / "chunk_embeddings.npy", matrix)
    (embedding_dir / "chunk_ids.json").write_text(
        json.dumps([row["chunk_id"] for row in chunk_rows], ensure_ascii=False, indent=2), encoding="utf-8"
    )
    manifest = {
        "provider": "e5",
        "model": model_name,
        "dimension": embedding_provider.dimensions,
        "normalized": True,
        "prefixes": {"query": "query: ", "passage": "passage: "},
        "document_count": len(documents),
        "chunk_count": len(chunks),
        "embedding_count": len(vectors),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    (embedding_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    # Persist the expensive model output before any database mutation so a
    # transient database/configuration problem cannot discard completed work.
    await asyncio.to_thread(_load_database, documents, chunks, vectors, database_url, model_name)
    return manifest


def load_cached_index(documents_path: Path, artifacts_root: Path, database_url: str, model_name: str) -> dict[str, int]:
    documents = [FatwaDocument.model_validate_json(line) for line in documents_path.read_text(encoding="utf-8").splitlines() if line.strip()]
    chunks = [chunk for document in documents for chunk in structure_aware_chunks(document)]
    matrix = np.load(artifacts_root / "embeddings" / "chunk_embeddings.npy")
    vectors = matrix.astype(np.float32).tolist()
    _validate_embeddings(chunks, vectors, int(matrix.shape[1]))
    _load_database(documents, chunks, vectors, database_url, model_name)
    return {"documents": len(documents), "chunks": len(chunks), "embeddings": len(vectors)}


def _chunk_artifact(chunk: FatwaChunk) -> dict[str, object]:
    chunk_id = str(stable_uuid("chunk", f"{chunk.fatwa_id}:{chunk.chunk_index}"))
    return {
        "chunk_id": chunk_id,
        "document_id": chunk.fatwa_id,
        "chunk_index": chunk.chunk_index,
        "text": chunk.content,
        "title": chunk.title,
        "source": chunk.source_collection.value,
        "canonical_reference": chunk.source_url,
        "category": chunk.category_path,
        "content_hash": hashlib.sha256(chunk.content.encode("utf-8")).hexdigest(),
    }


def _validate_embeddings(chunks: list[FatwaChunk], vectors: list[list[float]], dimensions: int) -> None:
    if len(chunks) != len(vectors):
        raise ValueError(f"Chunk/embedding count mismatch: {len(chunks)} != {len(vectors)}")
    chunk_keys = {(chunk.fatwa_id, chunk.chunk_index) for chunk in chunks}
    if len(chunk_keys) != len(chunks):
        raise ValueError("Duplicate chunk IDs detected")
    for index, vector in enumerate(vectors):
        if len(vector) != dimensions:
            raise ValueError(f"Embedding {index} has dimension {len(vector)}; expected {dimensions}")
        if not all(math.isfinite(value) for value in vector):
            raise ValueError(f"Embedding {index} contains NaN or Inf")


def _load_database(
    documents: list[FatwaDocument],
    chunks: list[FatwaChunk],
    vectors: list[list[float]],
    database_url: str,
    model_name: str,
) -> None:
    with psycopg.connect(psycopg_url(database_url)) as connection, connection.cursor() as cursor:
        cursor.execute("TRUNCATE embeddings, fatwa_chunks, fatwa_category_links, fatwas CASCADE")
        for document in documents:
            document_id = stable_uuid("document", f"{document.source_collection.value}:{document.external_id}")
            cursor.execute(
                """
                INSERT INTO fatwas (
                  id, external_id, title, question, answer, full_original_text, retrieval_text,
                  answer_segments, follow_up_dialogue, tags, source_collection, source_collection_name,
                  source_authority, source_author, scholar, scholars, madhhab, madhhabs, book, volume,
                  page, fatwa_number, category, subcategory, topic, evidence, original_reference,
                  qa_pairs, source_organization, source_domain, source_url, canonical_url, source_type,
                  language, audio_url, has_audio, original_metadata, scraped_at, content_hash
                ) VALUES (
                  %(id)s, %(external_id)s, %(title)s, %(question)s, %(answer)s, %(full_original_text)s,
                  %(retrieval_text)s, %(answer_segments)s::jsonb, %(follow_up_dialogue)s::jsonb, %(tags)s::jsonb,
                  %(source_collection)s, %(source_collection_name)s, %(source_authority)s, %(source_author)s,
                  %(scholar)s, %(scholars)s::jsonb, %(madhhab)s, %(madhhabs)s::jsonb, %(book)s, %(volume)s,
                  %(page)s, %(fatwa_number)s, %(category)s, %(subcategory)s, %(topic)s, %(evidence)s::jsonb,
                  %(original_reference)s::jsonb, %(qa_pairs)s::jsonb, %(source_organization)s, %(source_domain)s,
                  %(source_url)s, %(canonical_url)s, %(source_type)s, %(language)s, %(audio_url)s, %(has_audio)s,
                  %(original_metadata)s::jsonb, %(scraped_at)s, %(content_hash)s
                )
                """,
                {
                    **document.model_dump(mode="json"),
                    "id": document_id,
                    **{field: json.dumps(document.model_dump(mode="json")[field], ensure_ascii=False) for field in (
                        "answer_segments", "follow_up_dialogue", "tags", "scholars", "madhhabs", "evidence",
                        "original_reference", "qa_pairs", "original_metadata"
                    )},
                },
            )
        for chunk, vector in zip(chunks, vectors, strict=True):
            document_id = stable_uuid("document", f"{chunk.source_collection.value}:{chunk.fatwa_id}")
            chunk_id = stable_uuid("chunk", f"{chunk.fatwa_id}:{chunk.chunk_index}")
            cursor.execute(
                """
                INSERT INTO fatwa_chunks (id, fatwa_id, chunk_index, content, title, category_path, source_url,
                  source_collection, source_author, source_authority, token_count)
                VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s, %s, %s, %s, %s)
                """,
                (chunk_id, document_id, chunk.chunk_index, chunk.content, chunk.title,
                 json.dumps(chunk.category_path, ensure_ascii=False), chunk.source_url, chunk.source_collection.value,
                 chunk.source_author, chunk.source_authority, len(chunk.content.split())),
            )
            cursor.execute(
                "INSERT INTO embeddings (chunk_id, provider, model, dimensions, embedding) VALUES (%s, %s, %s, %s, %s::vector)",
                (chunk_id, "e5", model_name, len(vector), _vector_literal(vector)),
            )
        connection.commit()
