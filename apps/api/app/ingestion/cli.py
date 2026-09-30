import asyncio
import json
import hashlib
import math
from pathlib import Path
import typer
from app.config import get_settings
from app.ingestion.audit import build_audit, export_audit
from app.ingestion.crawler import ApprovedReferenceCrawler, ConservativeCrawler
from app.ingestion.parser import IbnBazFatwaParser
from app.ingestion.adapters import HackathonApprovedSourceAdapter
from app.models.domain import FatwaDocument
from app.providers.base import MockEmbeddingProvider
from app.providers.real import E5EmbeddingProvider
from app.rag.chunking import structure_aware_chunks
from app.ingestion.database import build_real_index, load_cached_index


app = typer.Typer(help="Source-aware Islamic knowledge ingestion stages.", no_args_is_help=True)
DATA = Path("data")
ARTIFACTS = Path("../../artifacts")


@app.command("approved-corpus")
def approved_corpus(
    limit: int = typer.Option(150, min=1, max=300, help="Controlled real-document target"),
    start_url: str = typer.Option("https://dorar.net/feqhia/1455", help="Approved content page from which to follow the site's Next links"),
    cache_dir: Path = typer.Option(Path("data/cache/dorar"), help="Local raw HTML cache (gitignored)"),
    output: Path = typer.Option(Path("../../artifacts/corpus/documents.jsonl"), help="Normalized auditable corpus manifest"),
) -> None:
    """Fetch and normalize a controlled corpus from the approved Dorar source."""
    settings = get_settings()
    crawler = ApprovedReferenceCrawler(cache_dir, settings.crawl_user_agent, settings.crawl_delay_seconds)
    urls = asyncio.run(crawler.discover_content_sequence(start_url, limit))
    if not urls:
        raise typer.BadParameter("No approved detail URLs were discovered from the official index")
    cached = asyncio.run(crawler.fetch_documents(urls))
    adapter = HackathonApprovedSourceAdapter()
    documents: list[FatwaDocument] = []
    failures: list[dict] = []
    for url, cache_file in cached.items():
        try:
            documents.append(adapter.parse(cache_file.read_text(encoding="utf-8"), url))
        except Exception as exc:
            failures.append({"url": url, "error": type(exc).__name__, "message": str(exc)})
    output.parent.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output, [document.model_dump(mode="json") for document in documents])
    failure_path = output.with_name("failures.json")
    failure_path.write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    audit_result = build_audit(documents, failures)
    export_audit(audit_result, output.with_name("audit.json"), output.with_name("audit.csv"))
    typer.echo(f"Discovered {len(urls)}; normalized {len(documents)} real approved documents; {len(failures)} failures")


@app.command("build-real-index")
def build_index(
    documents: Path = typer.Option(Path("../../artifacts/corpus/documents.jsonl")),
    artifacts_root: Path = typer.Option(Path("../../artifacts")),
) -> None:
    """Chunk, embed with real E5, persist artifacts, and load PostgreSQL."""
    settings = get_settings()
    provider = E5EmbeddingProvider(settings.e5_model)
    manifest = asyncio.run(
        build_real_index(documents, artifacts_root, settings.database_url, provider, settings.e5_model)
    )
    typer.echo(json.dumps(manifest, ensure_ascii=False))


@app.command("load-cached-index")
def load_index(
    documents: Path = typer.Option(Path("../../artifacts/corpus/documents.jsonl")),
    artifacts_root: Path = typer.Option(Path("../../artifacts")),
) -> None:
    """Load already persisted E5 vectors into PostgreSQL without recomputing."""
    settings = get_settings()
    result = load_cached_index(documents, artifacts_root, settings.database_url, settings.e5_model)
    typer.echo(json.dumps(result, ensure_ascii=False))


@app.command()
def crawl(seed: list[str] = typer.Option(..., help="Official category /fatwa URL"), max_categories: int | None = None) -> None:
    settings = get_settings()
    crawler = ConservativeCrawler(DATA / "cache", settings.crawl_user_agent, settings.crawl_delay_seconds)
    found = asyncio.run(crawler.discover(seed, max_categories))
    asyncio.run(crawler.fetch_documents(list(found.values())))
    path = DATA / "discovered.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {str(external_id): {"url": url, "cache_file": str(crawler.cache_path(url))} for external_id, url in found.items()}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"Discovered {len(found)} unique fatwa IDs -> {path}")


@app.command()
def parse() -> None:
    discovered_path = DATA / "discovered.json"
    if not discovered_path.exists():
        raise typer.BadParameter("Run crawl first; data/discovered.json is missing")
    discovered = json.loads(discovered_path.read_text(encoding="utf-8"))
    parser = IbnBazFatwaParser()
    records: list[dict] = []
    failures: list[dict] = []
    for external_id, item in discovered.items():
        cache_file = Path(item["cache_file"])
        try:
            document = parser.parse(cache_file.read_text(encoding="utf-8"), item["url"])
            records.append(document.model_dump(mode="json"))
        except Exception as exc:  # stage output must preserve failures for retry/audit
            failures.append({"external_id": int(external_id), "url": item["url"], "error": type(exc).__name__, "message": str(exc)})
    _write_jsonl(DATA / "parsed.jsonl", records)
    (DATA / "parse_failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"Parsed {len(records)} fatwas; {len(failures)} failures")


@app.command("sample-approved")
def sample_approved(
    fixtures_dir: Path = typer.Option(Path("tests/fixtures"), help="Controlled approved-source HTML sample directory"),
    output_dir: Path = typer.Option(Path("data/approved_sample"), help="Output directory for normalized sample records"),
) -> None:
    """Parse synthetic Dorar-shaped fixtures without redistributing source text."""
    adapter = HackathonApprovedSourceAdapter()
    records: list[dict] = []
    failures: list[dict] = []
    for fixture in sorted(fixtures_dir.glob("dorar_*.html")):
        external_id = fixture.stem.split("_")[-1]
        url = f"https://dorar.net/feqhia/{external_id}/"
        try:
            document = adapter.parse(fixture.read_text(encoding="utf-8"), url)
            records.append(document.model_dump(mode="json"))
        except Exception as exc:
            failures.append({"fixture": str(fixture), "url": url, "error": type(exc).__name__, "message": str(exc)})
    output_dir.mkdir(parents=True, exist_ok=True)
    _write_jsonl(output_dir / "validated.jsonl", records)
    (output_dir / "failures.json").write_text(json.dumps(failures, ensure_ascii=False, indent=2), encoding="utf-8")
    audit_result = build_audit([FatwaDocument.model_validate(item) for item in records], failures)
    export_audit(audit_result, output_dir / "audit.json", output_dir / "audit.csv")
    typer.echo(f"Parsed and validated {len(records)} approved-source documents; {len(failures)} failures")


@app.command()
def validate() -> None:
    documents = _read_documents()
    valid: list[dict] = []
    invalid: list[dict] = []
    seen: set[int] = set()
    for doc in documents:
        reasons: list[str] = []
        if doc.external_id in seen:
            reasons.append("duplicate external_id")
        seen.add(doc.external_id)
        if not doc.answer.strip():
            reasons.append("empty answer")
        expected = hashlib.sha256(doc.full_original_text.encode("utf-8")).hexdigest()
        if expected != doc.content_hash:
            reasons.append("content hash mismatch")
        (invalid if reasons else valid).append({"external_id": doc.external_id, "reasons": reasons} if reasons else doc.model_dump(mode="json"))
    _write_jsonl(DATA / "validated.jsonl", valid)
    (DATA / "validation_failures.json").write_text(json.dumps(invalid, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo(f"Validated {len(valid)} fatwas; {len(invalid)} rejected")


@app.command()
def audit(json_path: Path = Path("data/exports/audit.json"), csv_path: Path = Path("data/exports/audit.csv")) -> None:
    documents = _read_documents(DATA / "validated.jsonl")
    failure_path = DATA / "parse_failures.json"
    failures = json.loads(failure_path.read_text(encoding="utf-8")) if failure_path.exists() else []
    result = build_audit(documents, failures)
    export_audit(result, json_path, csv_path)
    typer.echo(f"Audit exported to {json_path} and {csv_path}")


@app.command()
def embed() -> None:
    documents = _read_documents(DATA / "validated.jsonl")
    chunks = [chunk for document in documents for chunk in structure_aware_chunks(document)]
    provider = MockEmbeddingProvider()
    vectors = asyncio.run(provider.embed([chunk.content for chunk in chunks]))
    records = [{**chunk.model_dump(mode="json"), "provider": "mock", "model": "deterministic-dev", "embedding": vector} for chunk, vector in zip(chunks, vectors, strict=True)]
    _write_jsonl(DATA / "embedded_chunks.jsonl", records)
    typer.echo(f"Embedded {len(records)} structure-aware chunks")


@app.command()
def reindex() -> None:
    embedded = DATA / "embedded_chunks.jsonl"
    if not embedded.exists():
        raise typer.BadParameter("Run embed first; embedded chunk output is missing")
    manifest = {"input": str(embedded), "lexical_index": "fatwas_retrieval_fts_idx", "vector_index": "embeddings_hnsw_idx", "status": "ready_for_database_load"}
    (DATA / "reindex_manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
    typer.echo("Prepared lexical/vector reindex manifest")


def _write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + ("\n" if rows else ""), encoding="utf-8")


def _read_documents(path: Path = DATA / "parsed.jsonl") -> list[FatwaDocument]:
    if not path.exists():
        raise typer.BadParameter(f"Required stage output is missing: {path}")
    return [FatwaDocument.model_validate_json(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


if __name__ == "__main__":
    app()
