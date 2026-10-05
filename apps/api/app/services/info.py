"""Facts about the running service, for the website's admin area and public pages."""
from __future__ import annotations

from collections import Counter
from datetime import datetime, timezone

from app.config import Settings
from app.services.final_rag import FinalRagService


def service_info(settings: Settings, service: FinalRagService) -> dict:
    """Model names and the real size of the loaded production index. Reads memory; calls no model."""
    # Root to leaf, as it appears in the encyclopedia: [book, chapter, section, ...].
    paths = [list(reversed(unit["hierarchy_original_leaf_to_root"])) for unit in service.units]
    books = Counter(path[0] for path in paths if path)
    chapters = Counter((path[0], path[1]) for path in paths if len(path) > 1)
    index_file = service.index_dir / "embeddings.npy"
    indexed_at = datetime.fromtimestamp(index_file.stat().st_mtime, tz=timezone.utc) if index_file.exists() else None

    return {
        "models": {
            "generation": settings.openai_generation_model,
            "embedding": service.manifest.get("model_name"),
            "reranker": service.manifest.get("reranker_model") if service.manifest.get("reranker_enabled") else None,
        },
        "index": {
            "documents": len(service.units),
            "chunks": int(service.embeddings.shape[0]),
            "indexed_at": indexed_at.isoformat() if indexed_at else None,
            "books": [{"title": title, "entries": entries} for title, entries in books.most_common()],
            "chapters": [{"book": book, "title": title, "entries": entries} for (book, title), entries in chapters.most_common()],
        },
    }
