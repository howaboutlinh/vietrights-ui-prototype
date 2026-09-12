from types import SimpleNamespace
import pytest
from services.config import ConfigurationError, Settings
from services.embedding_service import EmbeddingError, EmbeddingService
from services.retrieval import retrieve_context, rewrite_search_query

def settings(**changes):
    base = Settings(gemini_api_key="x", database_url="postgresql://db-user:secret@pooler.example/postgres")
    return Settings(**{**base.__dict__, **changes})

def test_translation_falls_back_to_original():
    client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **_: (_ for _ in ()).throw(RuntimeError("offline"))))
    question = "Tôi được trả $15 một giờ bằng tiền mặt và không có payslip."
    assert rewrite_search_query(question, settings(), client) == question

def test_embedding_failure_is_wrapped():
    client = SimpleNamespace(models=SimpleNamespace(embed_content=lambda **_: (_ for _ in ()).throw(RuntimeError("offline"))))
    with pytest.raises(EmbeddingError): EmbeddingService(settings(), client, max_retries=1).embed_query("pay rights")

def test_no_results_below_threshold():
    embedder = SimpleNamespace(embed_query=lambda _: [0.0] * 768)
    store = SimpleNamespace(match=lambda *_: [{"content": "weak", "similarity": 0.59}])
    rewrite = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **_: SimpleNamespace(text="cash pay without payslip")))
    assert retrieve_context({"mainIssues": ["pay"]}, settings(), embedder, store, rewrite) == []

def test_missing_environment_variables_are_rejected():
    with pytest.raises(ConfigurationError): Settings().validate(["gemini_api_key", "database_url"])
