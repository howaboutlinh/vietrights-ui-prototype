import services.llm
from app import app
from services.config import ConfigurationError
from types import SimpleNamespace
import json

SCENARIO = {"mainIssues": ["pay", "payslip"], "description": "Tôi được trả $15 một giờ bằng tiền mặt và không có payslip.", "language": "vi"}

def test_api_returns_safe_no_evidence_response(monkeypatch):
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [])
    response = app.test_client().post("/analyze", json=SCENARIO)
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["answer"] and payload["sources"] == []
    assert payload["retrieval"] == {"used": True, "result_count": 0}

def test_frontend_response_does_not_expose_secrets(monkeypatch):
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [])
    serialized = str(app.test_client().post("/analyze", json=SCENARIO).get_json()).lower()
    assert "service_role" not in serialized and "database_url" not in serialized and "embedding" not in serialized

def test_api_handles_missing_rag_configuration(monkeypatch):
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: (_ for _ in ()).throw(ConfigurationError("missing secret")))
    response = app.test_client().post("/analyze", json=SCENARIO)
    payload = response.get_json()
    assert response.status_code == 503
    assert payload["error_code"] == "service_unconfigured"
    assert "missing secret" not in str(payload)

def test_api_response_contains_grounded_answer_and_sources(monkeypatch):
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [{
        "source_name": "Fair Work Ombudsman", "source_url": "https://fairwork.gov.au/pay",
        "document_title": "Minimum wages", "section_title": "Pay slips",
        "content": "Employers must provide pay slips.", "similarity": 0.83,
    }])
    model_result = {
        "summary": "Bạn nên kiểm tra mức lương và phiếu lương [1].", "issues": ["Có thể có vấn đề về lương [1]."],
        "evidence": ["Giữ lại lịch làm việc [1]."], "next_steps": ["Liên hệ Fair Work [1]."],
        "clarification_questions": [], "risk_level": "medium", "sources": [],
    }
    models = SimpleNamespace(generate_content=lambda **_: SimpleNamespace(text=json.dumps(model_result, ensure_ascii=False)))
    monkeypatch.setattr(services.llm, "_get_gemini_client", lambda: SimpleNamespace(models=models))
    payload = app.test_client().post("/analyze", json=SCENARIO).get_json()
    assert payload["answer"].endswith("[1].")
    assert payload["sources"][0]["number"] == 1
    assert payload["sources"][0]["section"] == "Pay slips"
    assert payload["retrieval"]["result_count"] == 1
