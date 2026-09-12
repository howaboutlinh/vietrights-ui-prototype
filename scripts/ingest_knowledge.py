#!/usr/bin/env python3
"""Crawl, extract, chunk, embed and upsert the four approved sources."""
from __future__ import annotations
import argparse
import logging
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from services.chunking import KnowledgeChunk, chunk_document
from services.config import ConfigurationError, Settings, knowledge_sources
from services.embedding_service import EmbeddingService
from services.source_loader import SourceCrawler
from services.vector_store import SupabaseVectorStore

logger = logging.getLogger("vietrights.ingest")

def batches(values: list[KnowledgeChunk], size: int = 16):
    for start in range(0, len(values), size):
        yield values[start:start + size]

def run(source_number: int | None = None, dry_run: bool = False) -> dict[str, int]:
    """Run bounded ingestion and return aggregate statistics."""
    settings = Settings.from_env()
    sources = knowledge_sources()
    if source_number is not None:
        if source_number not in range(1, 5):
            raise ConfigurationError("--source must be between 1 and 4.")
        sources = [sources[source_number - 1]]
    crawler = SourceCrawler(settings.request_timeout_seconds, settings.crawl_max_depth, settings.crawl_max_pages)
    embedder = None if dry_run else EmbeddingService(settings)
    store = None if dry_run else SupabaseVectorStore(settings)
    stats = {"urls_processed": 0, "pdfs_processed": 0, "chunks_created": 0, "chunks_skipped": 0, "chunks_updated": 0, "failures": 0}
    for source_url in sources:
        documents, failures = crawler.crawl(source_url)
        stats["failures"] += len(failures)
        chunks: list[KnowledgeChunk] = []
        for document in documents:
            stats["urls_processed"] += 1
            stats["pdfs_processed"] += int(document.document_type == "pdf")
            chunks.extend(chunk_document(document))
        if dry_run:
            stats["chunks_created"] += len(chunks)
            continue
        assert embedder is not None and store is not None
        for group in batches(chunks):
            vectors = embedder.embed_documents([chunk.content for chunk in group])
            result = store.upsert_chunks(group, vectors)
            stats["chunks_created"] += result["created"]
            stats["chunks_skipped"] += result["skipped"]
            stats["chunks_updated"] += result["updated"]
    return stats

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=int, choices=range(1, 5), help="Ingest only source 1-4")
    parser.add_argument("--dry-run", action="store_true", help="Extract/chunk without Gemini or Supabase")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s %(message)s")
    try:
        stats = run(args.source, args.dry_run)
    except ConfigurationError as exc:
        logger.error("Configuration error: %s", exc)
        return 2
    except Exception as exc:
        logger.error("Ingestion failed: %s", exc)
        return 1
    for key, value in stats.items():
        print(f"{key}: {value}")
    return 0 if not stats["failures"] else 1

if __name__ == "__main__":
    raise SystemExit(main())
