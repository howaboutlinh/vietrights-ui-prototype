"""Transactional SQLAlchemy storage and pgvector cosine retrieval."""

from __future__ import annotations

from typing import Any, Iterable

from sqlalchemy import or_, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import SQLAlchemyError

from services.chunking import KnowledgeChunk as ChunkPayload
from services.config import Settings
from services.database import db
from services.models import KnowledgeChunk as KnowledgeChunkModel


class VectorStoreError(RuntimeError):
    """Raised when vector persistence or retrieval fails safely."""


class SQLAlchemyVectorStore:
    """Persist and search knowledge chunks through the Flask-managed session."""

    def __init__(self, settings: Settings | None = None, session: Any | None = None):
        self.settings = settings or Settings.from_env()
        self.settings.validate(["database_url"])
        self.session = session if session is not None else db.session

    def existing_hashes(self, hashes: Iterable[str]) -> set[str]:
        """Return hashes already present in PostgreSQL."""
        values = list(dict.fromkeys(hashes))
        if not values:
            return set()
        try:
            statement = select(KnowledgeChunkModel.content_hash).where(KnowledgeChunkModel.content_hash.in_(values))
            return {str(value) for value in self.session.scalars(statement).all()}
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise VectorStoreError("Unable to check existing knowledge chunks.") from exc

    @staticmethod
    def _row(chunk: ChunkPayload, embedding: list[float]) -> dict[str, Any]:
        return {
            "source_name": chunk.source_name,
            "source_url": chunk.source_url,
            "document_title": chunk.document_title,
            "document_type": chunk.document_type,
            "section_title": chunk.section_title,
            "content": chunk.content,
            "content_hash": chunk.content_hash,
            "chunk_index": chunk.chunk_index,
            "metadata": chunk.metadata,
            "embedding": embedding,
        }

    def upsert_chunks(self, chunks: list[ChunkPayload], embeddings: list[list[float]]) -> dict[str, int]:
        """Insert new hashes atomically and ignore duplicates, including concurrent ones."""
        if len(chunks) != len(embeddings):
            raise ValueError("Each chunk must have exactly one embedding.")
        if any(len(vector) != self.settings.embedding_dimension for vector in embeddings):
            raise ValueError("Embedding dimension does not match EMBEDDING_DIMENSION.")
        if not chunks:
            return {"created": 0, "skipped": 0, "updated": 0}
        rows = [self._row(chunk, vector) for chunk, vector in zip(chunks, embeddings)]
        table = KnowledgeChunkModel.__table__
        statement = (
            insert(table)
            .values(rows)
            .on_conflict_do_nothing(index_elements=[table.c.content_hash])
            .returning(table.c.content_hash)
        )
        try:
            created_hashes = list(self.session.scalars(statement).all())
            self.session.commit()
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise VectorStoreError("Unable to store knowledge chunks.") from exc
        created = len(created_hashes)
        return {"created": created, "skipped": len(chunks) - created, "updated": 0}

    def match(self, embedding: list[float], threshold: float, count: int) -> list[dict[str, Any]]:
        """Return highest cosine-similarity chunks above the configured threshold."""
        if len(embedding) != self.settings.embedding_dimension:
            raise VectorStoreError("Query embedding dimension does not match the database schema.")
        distance = KnowledgeChunkModel.embedding.cosine_distance(embedding)
        similarity = (1 - distance).label("similarity")
        statement = (
            select(
                KnowledgeChunkModel.id,
                KnowledgeChunkModel.source_name,
                KnowledgeChunkModel.source_url,
                KnowledgeChunkModel.document_title,
                KnowledgeChunkModel.document_type,
                KnowledgeChunkModel.section_title,
                KnowledgeChunkModel.content,
                KnowledgeChunkModel.content_hash,
                KnowledgeChunkModel.chunk_metadata.label("metadata"),
                similarity,
            )
            .where(similarity >= float(threshold))
            .order_by(distance.asc())
            .limit(max(0, int(count)))
        )
        try:
            return [dict(row) for row in self.session.execute(statement).mappings().all()]
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise VectorStoreError("Unable to search the knowledge base.") from exc

    @staticmethod
    def _public_columns():
        """Columns that may be returned to the agent; embeddings never leave storage."""
        return (
            KnowledgeChunkModel.id,
            KnowledgeChunkModel.source_name,
            KnowledgeChunkModel.source_url,
            KnowledgeChunkModel.document_title,
            KnowledgeChunkModel.document_type,
            KnowledgeChunkModel.section_title,
            KnowledgeChunkModel.content,
            KnowledgeChunkModel.content_hash,
            KnowledgeChunkModel.chunk_index,
            KnowledgeChunkModel.chunk_metadata.label("metadata"),
        )

    def surrounding_chunks(self, chunk_id: int, radius: int = 1) -> list[dict[str, Any]]:
        """Read adjacent chunks from the same source document."""
        radius = min(max(int(radius), 0), 2)
        try:
            anchor = self.session.execute(
                select(KnowledgeChunkModel.source_url, KnowledgeChunkModel.chunk_index)
                .where(KnowledgeChunkModel.id == int(chunk_id))
            ).one_or_none()
            if anchor is None:
                return []
            statement = (
                select(*self._public_columns())
                .where(
                    KnowledgeChunkModel.source_url == anchor.source_url,
                    KnowledgeChunkModel.chunk_index.between(
                        anchor.chunk_index - radius, anchor.chunk_index + radius
                    ),
                )
                .order_by(KnowledgeChunkModel.chunk_index.asc())
            )
            return [dict(row) for row in self.session.execute(statement).mappings().all()]
        except (SQLAlchemyError, TypeError, ValueError) as exc:
            self.session.rollback()
            raise VectorStoreError("Unable to fetch surrounding knowledge chunks.") from exc

    def source_sections(self, source_url: str, section: str = "", count: int = 4) -> list[dict[str, Any]]:
        """Read bounded chunks from one already-indexed official source."""
        count = min(max(int(count), 1), 6)
        statement = select(*self._public_columns()).where(KnowledgeChunkModel.source_url == str(source_url))
        clean_section = str(section or "").strip()
        if clean_section:
            pattern = f"%{clean_section[:120]}%"
            statement = statement.where(or_(
                KnowledgeChunkModel.section_title.ilike(pattern),
                KnowledgeChunkModel.content.ilike(pattern),
            ))
        statement = statement.order_by(KnowledgeChunkModel.chunk_index.asc()).limit(count)
        try:
            return [dict(row) for row in self.session.execute(statement).mappings().all()]
        except SQLAlchemyError as exc:
            self.session.rollback()
            raise VectorStoreError("Unable to fetch source sections.") from exc
