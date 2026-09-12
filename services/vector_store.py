"""Server-only Supabase storage and pgvector similarity RPC access."""
from __future__ import annotations
from dataclasses import asdict
from typing import Any, Iterable
from services.chunking import KnowledgeChunk
from services.config import Settings

class VectorStoreError(RuntimeError):
    """Raised when vector persistence or retrieval fails safely."""

class SupabaseVectorStore:
    """Small adapter around the privileged server-side Supabase client."""
    def __init__(self, settings: Settings | None = None, client: Any | None = None):
        self.settings = settings or Settings.from_env()
        self.settings.validate(["supabase_url", "supabase_service_role_key"])
        if client is None:
            from supabase import create_client
            client = create_client(self.settings.supabase_url, self.settings.supabase_service_role_key)
        self.client = client

    def existing_hashes(self, hashes: Iterable[str]) -> set[str]:
        values = list(dict.fromkeys(hashes))
        if not values:
            return set()
        try:
            response = self.client.table("knowledge_chunks").select("content_hash").in_("content_hash", values).execute()
            return {str(row["content_hash"]) for row in (response.data or [])}
        except Exception as exc:
            raise VectorStoreError("Unable to check existing knowledge chunks.") from exc

    def upsert_chunks(self, chunks: list[KnowledgeChunk], embeddings: list[list[float]]) -> dict[str, int]:
        if len(chunks) != len(embeddings):
            raise ValueError("Each chunk must have exactly one embedding.")
        existing = self.existing_hashes(chunk.content_hash for chunk in chunks)
        new_pairs = [(chunk, vector) for chunk, vector in zip(chunks, embeddings) if chunk.content_hash not in existing]
        if new_pairs:
            rows = []
            for chunk, vector in new_pairs:
                row = asdict(chunk)
                row["embedding"] = vector
                rows.append(row)
            try:
                self.client.table("knowledge_chunks").upsert(rows, on_conflict="content_hash").execute()
            except Exception as exc:
                raise VectorStoreError("Unable to store knowledge chunks.") from exc
        return {"created": len(new_pairs), "skipped": len(chunks) - len(new_pairs), "updated": 0}

    def match(self, embedding: list[float], threshold: float, count: int) -> list[dict[str, Any]]:
        if len(embedding) != self.settings.embedding_dimension:
            raise VectorStoreError("Query embedding dimension does not match the database schema.")
        try:
            response = self.client.rpc("match_knowledge_chunks", {"query_embedding": embedding, "match_threshold": float(threshold), "match_count": int(count)}).execute()
            return [dict(row) for row in (response.data or [])]
        except Exception as exc:
            raise VectorStoreError("Unable to search the knowledge base.") from exc
