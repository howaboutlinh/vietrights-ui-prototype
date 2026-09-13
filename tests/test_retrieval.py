from types import SimpleNamespace
import pytest
from services.config import ConfigurationError, Settings
from services.embedding_service import EmbeddingError, EmbeddingService
from services.retrieval import KnowledgeTools, MAX_PLANNING_ROUNDS, case_to_question, compact_case_data, retrieve_context, rewrite_search_query

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

def test_agent_tool_loop_is_bounded_and_deduplicates_results():
    calls = []
    function_call = SimpleNamespace(name="search_knowledge", args={"query": "minimum wage cash pay", "limit": 6})
    class Models:
        def generate_content(self, **kwargs):
            calls.append(kwargs)
            return SimpleNamespace(function_calls=[function_call], candidates=[])
    embedder = SimpleNamespace(embed_query=lambda _: [0.0] * 768)
    row = {"id": 7, "content_hash": "same", "content": "official evidence", "source_url": "https://example.gov.au/pay", "similarity": 0.9}
    store = SimpleNamespace(match=lambda *_: [row])
    result = retrieve_context({"mainIssues": ["pay"]}, settings(), embedder, store, SimpleNamespace(models=Models()))
    assert len(calls) == MAX_PLANNING_ROUNDS
    assert result == [row]

def test_source_section_tool_only_accepts_urls_returned_by_search():
    embedder = SimpleNamespace(embed_query=lambda _: [0.0] * 768)
    store = SimpleNamespace(
        match=lambda *_: [{"source_url": "https://official.example/pay"}],
        source_sections=lambda *args: [{"content": "section", "source_url": args[0]}],
    )
    tools = KnowledgeTools(settings(), embedder, store)
    assert tools.call("get_source_sections", {"source_url": "https://untrusted.example"}) == []
    tools.call("search_knowledge", {"query": "pay", "limit": 1})
    assert tools.call("get_source_sections", {"source_url": "https://official.example/pay"})[0]["content"] == "section"

def test_complete_intake_is_sent_to_research_agent():
    payload = {"mainIssues": ["visa"], "description": "Tôi bị đe doạ", "nested": {"hours": 60}}
    serialized = case_to_question(payload)
    assert "Tôi bị đe doạ" in serialized and '"nested"' not in serialized


def test_compact_case_removes_empty_fields_and_preserves_unicode_unknowns():
    compact = compact_case_data({
        "language": "vi", "mainIssues": ["pay", "pay"], "description": "Tôi được trả lương.",
        "paidLeave": "unknown", "documentAvailability": "payslip_only",
        "has_contract": False, "has_payslip": True, "pay": {"payBasis": "hourly", "amount": 25},
        "workTime": ["weekend"], "empty": "", "none": None,
    })
    assert compact["issue"] == "Tôi được trả lương."
    assert compact["risk_flags"] == ["pay"]
    assert compact["contract"] == "no" and compact["payslip"] == "yes"
    assert compact["paidLeave"] == "unknown"
    assert "empty" not in compact and "none" not in compact


def test_compact_case_json_is_unicode_and_in_memory():
    payload = {"mainIssues": ["payslip"], "description": "Không có payslip"}
    serialized = case_to_question(payload)
    assert "Không có payslip" in serialized
    assert "\\u00" not in serialized


def test_compact_case_does_not_write_a_physical_json_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    case_to_question({"mainIssues": ["pay"], "description": "Tôi được trả thiếu."})
    assert list(tmp_path.iterdir()) == []
