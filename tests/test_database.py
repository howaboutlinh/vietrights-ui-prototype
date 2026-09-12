from types import SimpleNamespace

import pytest
from sqlalchemy.dialects import postgresql
from sqlalchemy.exc import OperationalError

from services.chunking import KnowledgeChunk
from services.config import Settings
from services.models import KnowledgeChunk as KnowledgeChunkModel
from services.vector_store import SQLAlchemyVectorStore, VectorStoreError


def settings():
    return Settings(database_url="postgresql://db-user:secret@pooler.example/postgres")


def chunk(hash_value: str = "hash-1") -> KnowledgeChunk:
    return KnowledgeChunk(
        source_name="Fair Work Ombudsman",
        source_url="https://fairwork.gov.au/pay",
        document_title="Pay guide",
        document_type="html",
        section_title="Minimum wages",
        content="Official source content",
        content_hash=hash_value,
        chunk_index=0,
        metadata={"page_number": 1},
    )


class ScalarResult:
    def __init__(self, values):
        self.values = values

    def all(self):
        return self.values


class InsertSession:
    def __init__(self, returned_hashes=None, error=None):
        self.returned_hashes = returned_hashes or []
        self.error = error
        self.committed = False
        self.rolled_back = False
        self.statement = None

    def scalars(self, statement):
        self.statement = statement
        if self.error:
            raise self.error
        return ScalarResult(self.returned_hashes)

    def commit(self):
        self.committed = True

    def rollback(self):
        self.rolled_back = True


def test_model_matches_migration_columns():
    table = KnowledgeChunkModel.__table__
    assert set(table.columns.keys()) == {
        "id", "source_name", "source_url", "document_title", "document_type",
        "section_title", "content", "content_hash", "chunk_index", "metadata",
        "embedding", "created_at", "updated_at",
    }
    assert KnowledgeChunkModel.chunk_metadata.property.columns[0].name == "metadata"
    assert str(table.columns.embedding.type) == "VECTOR(768)"


def test_insertion_commits_transaction():
    session = InsertSession(["hash-1"])
    result = SQLAlchemyVectorStore(settings(), session).upsert_chunks([chunk()], [[0.0] * 768])
    assert result == {"created": 1, "skipped": 0, "updated": 0}
    assert session.committed and not session.rolled_back
    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "ON CONFLICT (content_hash) DO NOTHING" in sql


def test_duplicate_hash_is_skipped_without_failure():
    session = InsertSession([])
    result = SQLAlchemyVectorStore(settings(), session).upsert_chunks([chunk()], [[0.0] * 768])
    assert result["created"] == 0 and result["skipped"] == 1
    assert session.committed


def test_database_exception_rolls_back_transaction():
    error = OperationalError("insert", {}, RuntimeError("database unavailable"))
    session = InsertSession(error=error)
    with pytest.raises(VectorStoreError):
        SQLAlchemyVectorStore(settings(), session).upsert_chunks([chunk()], [[0.0] * 768])
    assert session.rolled_back and not session.committed


def test_cosine_retrieval_maps_rows_in_database_order():
    rows = [
        {"id": 1, "content": "best", "similarity": 0.91},
        {"id": 2, "content": "second", "similarity": 0.80},
    ]

    class MappingResult:
        def mappings(self): return self
        def all(self): return rows

    class QuerySession:
        rolled_back = False
        def execute(self, statement):
            self.statement = statement
            return MappingResult()
        def rollback(self): self.rolled_back = True

    session = QuerySession()
    result = SQLAlchemyVectorStore(settings(), session).match([0.0] * 768, 0.6, 6)
    assert [item["similarity"] for item in result] == [0.91, 0.80]
    sql = str(session.statement.compile(dialect=postgresql.dialect()))
    assert "<=>" in sql and "ORDER BY" in sql
    assert not session.rolled_back
