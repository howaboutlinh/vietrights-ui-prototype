from types import SimpleNamespace
import pytest
from services.config import ConfigurationError, Settings
from services.embedding_service import EmbeddingError, EmbeddingService
from services.retrieval import retrieve_context, rewrite_search_query
from services.vector_store import SupabaseVectorStore

def settings(**changes):
    base = Settings(gemini_api_key="x", supabase_url="https://project.supabase.co", supabase_service_role_key="secret")
    return Settings(**{**base.__dict__, **changes})

def test_translation_falls_back_to_original():
    client = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **_: (_ for _ in ()).throw(RuntimeError("offline"))))
    question = "Tôi được trả $15 một giờ bằng tiền mặt và không có payslip."
    assert rewrite_search_query(question, settings(), client) == question

def test_embedding_failure_is_wrapped():
    client = SimpleNamespace(models=SimpleNamespace(embed_content=lambda **_: (_ for _ in ()).throw(RuntimeError("offline"))))
    with pytest.raises(EmbeddingError): EmbeddingService(settings(), client, max_retries=1).embed_query("pay rights")

def test_supabase_similarity_result_mapping():
    response = SimpleNamespace(data=[{"id": 1, "content": "evidence", "similarity": 0.8}])
    client = SimpleNamespace(rpc=lambda *_args, **_kwargs: SimpleNamespace(execute=lambda: response))
    assert SupabaseVectorStore(settings(), client).match([0.0] * 768, 0.6, 6)[0]["similarity"] == 0.8

def test_no_results_below_threshold():
    embedder = SimpleNamespace(embed_query=lambda _: [0.0] * 768)
    store = SimpleNamespace(match=lambda *_: [{"content": "weak", "similarity": 0.59}])
    rewrite = SimpleNamespace(models=SimpleNamespace(generate_content=lambda **_: SimpleNamespace(text="cash pay without payslip")))
    assert retrieve_context({"mainIssues": ["pay"]}, settings(), embedder, store, rewrite) == []

def test_missing_environment_variables_are_rejected():
    with pytest.raises(ConfigurationError): Settings().validate(["gemini_api_key", "supabase_url", "supabase_service_role_key"])
