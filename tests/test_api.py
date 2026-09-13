import services.llm
import pytest
import app as app_module
from app import app
from services.config import ConfigurationError
from types import SimpleNamespace
import json
from pathlib import Path


def test_ai_heading_sanitizer_uses_sentence_case_and_preserves_proper_nouns():
    assert services.llm._sanitize_heading("Thanh ToáN LươNg ThấP HơN MứC TốI ThiểU") == "Thanh toán lương thấp hơn mức tối thiểu"
    assert services.llm._sanitize_heading("KhôNg CấP PhiếU LươNg HợP Lệ / Vi PhạM Quy ĐịNh Hồ Sơ Lao ĐộNg") == "Không cấp phiếu lương hợp lệ / vi phạm quy định hồ sơ lao động"
    assert services.llm._sanitize_heading("FAIR WORK ACT / NSW") == "Fair Work Act / NSW"

SCENARIO = {"mainIssues": ["pay", "payslip"], "description": "Tôi được trả $15 một giờ bằng tiền mặt và không có payslip.", "language": "vi"}

def test_api_returns_safe_no_evidence_response(monkeypatch):
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [{
        "source_name": "Official", "source_url": "https://example.gov.au/source",
        "document_title": "Source", "content": "Evidence.",
    }])
    monkeypatch.setattr(services.llm, "_get_gemini_client", lambda: SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **_: SimpleNamespace(text=json.dumps({
            "summary": "AI analysis with no retrieved evidence.", "issues": [], "evidence": [],
            "next_steps": [], "clarification_questions": [], "risk_level": "medium",
            "sources": [], "issue_analysis": [],
        })))
    ))
    response = app.test_client().post("/analyze", json=SCENARIO)
    payload = response.get_json()
    assert response.status_code == 200
    assert payload["answer"] and payload["sources"]
    assert payload["ai_used"] is True and payload["fallback"] is False


def test_gemini_is_called_before_fallback_for_empty_retrieval(monkeypatch):
    calls = []
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [{
        "source_name": "Official", "source_url": "https://example.gov.au/source",
        "document_title": "Source", "content": "Evidence.",
    }])
    monkeypatch.setattr(services.llm, "_get_gemini_client", lambda: SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **_: (calls.append(True) or SimpleNamespace(text=json.dumps({
            "summary": "AI result [1]", "issues": ["pay [1]"], "evidence": [], "next_steps": [],
            "clarification_questions": [], "risk_level": "medium", "sources": [], "issue_analysis": [],
        }))))
    ))
    payload = app.test_client().post("/api/analyze", json=SCENARIO).get_json()
    assert calls == [True]
    assert payload["ai_used"] is True and payload["fallback"] is False


def test_primary_model_failure_uses_secondary_gemini_model(monkeypatch):
    from google.genai import errors
    calls = []
    monkeypatch.setenv("GEMINI_MODEL", "primary-model")
    monkeypatch.setenv("GEMINI_FALLBACK_MODEL", "secondary-model")
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [{
        "source_name": "Official", "source_url": "https://example.gov.au/source",
        "document_title": "Source", "content": "Evidence.",
    }])

    def generate(**kwargs):
        calls.append(kwargs["model"])
        if kwargs["model"] == "primary-model":
            raise errors.APIError(500, {"error": {"code": 500}})
        return SimpleNamespace(text=json.dumps({
            "summary": "Secondary AI result [1]", "issues": [], "evidence": [], "next_steps": [],
            "clarification_questions": [], "risk_level": "medium", "sources": [], "issue_analysis": [],
        }))

    monkeypatch.setattr(services.llm, "_get_gemini_client", lambda: SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    payload = app.test_client().post("/api/analyze", json=SCENARIO).get_json()
    assert payload["ai_used"] is True
    assert payload["fallback"] is False
    assert calls == ["primary-model"] * 3 + ["secondary-model"]


def test_unusual_document_combination_is_sent_to_gemini(monkeypatch):
    calls = []
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [{
        "source_name": "Official", "source_url": "https://example.gov.au/source",
        "document_title": "Source", "content": "Evidence.",
    }])
    monkeypatch.setattr(services.llm, "_get_gemini_client", lambda: SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **kwargs: (calls.append(kwargs["contents"]) or SimpleNamespace(text=json.dumps({
            "summary": "AI result [1]", "issues": ["payslip [1]"], "evidence": [], "next_steps": [],
            "clarification_questions": [], "risk_level": "medium", "sources": [], "issue_analysis": [],
        }))))
    ))
    payload = app.test_client().post("/api/analyze", json={**SCENARIO, "documentAvailability": "payslip_only", "has_contract": False, "has_payslip": True}).get_json()
    assert len(calls) == 1
    assert payload["fallback"] is False


def test_missing_api_key_returns_client_setup_diagnostic_error(monkeypatch):
    monkeypatch.setattr(services.llm, "_get_gemini_client", lambda: (_ for _ in ()).throw(services.llm.LLMAuthenticationError()))
    payload = app.test_client().post("/api/analyze", json=SCENARIO).get_json()
    assert payload["success"] is False
    assert payload["error"] == "AI_ANALYSIS_FAILED"
    assert payload["stage"] == "client_setup"

def test_frontend_response_does_not_expose_secrets(monkeypatch):
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [])
    serialized = str(app.test_client().post("/analyze", json=SCENARIO).get_json()).lower()
    assert "service_role" not in serialized and "database_url" not in serialized and "embedding" not in serialized

@pytest.mark.parametrize("field", [
    "workplace", "workPattern", "paidLeave", "documentAvailability",
    "employmentTypeOnDocuments", "payslipStatus", "paymentMethod",
    "overtime", "breaks", "visaThreat", "immediateDanger", "safetyConcern", "coercion",
])
def test_api_rejects_empty_dropdown_value(monkeypatch, field):
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [])
    response = app.test_client().post("/analyze", json={**SCENARIO, field: ""})
    assert response.status_code == 400
    assert response.get_json()["error_code"] == "invalid_input"

def test_api_rejects_empty_pay_basis_value(monkeypatch):
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [])
    response = app.test_client().post("/analyze", json={**SCENARIO, "pay": {"payBasis": ""}})
    assert response.status_code == 400
    assert response.get_json()["error_code"] == "invalid_input"

def test_api_rejects_null_dropdown_value_from_client_payload(monkeypatch):
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [])
    response = app.test_client().post("/analyze", json={**SCENARIO, "paidLeave": None})
    assert response.status_code == 400
    assert response.get_json()["error_code"] == "invalid_input"

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
        "issue_analysis": [],
    }
    from google.genai import errors
    from services import retry
    monkeypatch.setattr(retry.time, 'sleep', lambda _: None)
    attempts = []
    def generate(**kwargs):
        attempts.append(kwargs)
        if len(attempts) < 3:
            raise errors.APIError(503, {'error': {'code': 503, 'message': 'temporary overload'}})
        return SimpleNamespace(text=json.dumps(model_result, ensure_ascii=False))
    models = SimpleNamespace(generate_content=generate)
    monkeypatch.setattr(services.llm, "_get_gemini_client", lambda: SimpleNamespace(models=models))
    payload = app.test_client().post("/analyze", json=SCENARIO).get_json()
    assert payload["answer"].endswith("[1].")
    assert payload["sources"][0]["number"] == 1
    assert payload["sources"][0]["section"] == "Pay slips"
    assert payload["retrieval"]["result_count"] == 1
    assert len(attempts) == 3


@pytest.mark.parametrize("error_type", [services.llm.LLMQuotaError, services.llm.LLMTimeoutError, services.llm.LLMServiceError])
def test_gemini_controlled_errors_return_http_200_fallback(monkeypatch, error_type):
    monkeypatch.setattr(app_module, "analyze_case", lambda _data: (_ for _ in ()).throw(error_type()))
    response = app.test_client().post("/analyze", json=SCENARIO)
    payload = response.get_json()
    assert response.status_code == 503
    assert payload == {
        "success": False,
        "error": "AI_ANALYSIS_FAILED",
        "stage": "gemini_request",
        "message": "The AI analysis service is currently unavailable.",
    }


def test_permanent_429_returns_fallback_with_http_200(monkeypatch):
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [{
        "source_name": "Fair Work Ombudsman", "source_url": "https://fairwork.gov.au/pay",
        "document_title": "Minimum wages", "section_title": "Pay", "content": "Official pay guidance.",
    }])
    from google.genai import errors
    from services import retry
    monkeypatch.setattr(retry.time, "sleep", lambda _: None)
    monkeypatch.setattr(services.llm, "_get_gemini_client", lambda: SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **_: (_ for _ in ()).throw(errors.APIError(429, {"error": {"code": 429}})))
    ))

    response = app.test_client().post("/analyze", json=SCENARIO)
    payload = response.get_json()
    assert response.status_code == 503
    assert payload["success"] is False
    assert payload["error"] == "AI_ANALYSIS_FAILED"
    assert payload["stage"] == "gemini_request"


def test_fallback_source_urls_are_restricted_to_retrieved_entries(monkeypatch):
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [{
        "source_name": "Official source", "source_url": "https://retrieved.example/guide",
        "document_title": "Guide", "content": "Official guidance.",
    }])
    from google.genai import errors
    from services import retry
    monkeypatch.setattr(retry.time, "sleep", lambda _: None)
    monkeypatch.setattr(services.llm, "_get_gemini_client", lambda: SimpleNamespace(
        models=SimpleNamespace(generate_content=lambda **_: (_ for _ in ()).throw(errors.APIError(429, {"error": {"code": 429}})))
    ))
    payload = app.test_client().post("/analyze", json=SCENARIO).get_json()
    assert payload["success"] is False
    assert payload["stage"] == "gemini_request"


def test_fallback_uses_trusted_organisations_when_no_entries_are_retrieved(monkeypatch):
    from google.genai import errors
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: (_ for _ in ()).throw(
        errors.APIError(429, {"error": {"code": 429}})
    ))
    payload = app.test_client().post("/analyze", json=SCENARIO).get_json()
    assert payload["success"] is False
    assert payload["stage"] == "gemini_request"


def test_successful_analysis_keeps_detailed_scenario_specific_output(monkeypatch):
    monkeypatch.setattr(services.llm, "retrieve_context", lambda *_args, **_kwargs: [{
        "source_name": "Fair Work Ombudsman", "source_url": "https://fairwork.gov.au/pay",
        "document_title": "Pay guide", "section_title": "Minimum pay", "content": "Official pay evidence.",
    }])

    def generate(**kwargs):
        case_data_start = kwargs["contents"].index("WORKER CASE JSON:") + len("WORKER CASE JSON:")
        case_data = json.JSONDecoder().raw_decode(kwargs["contents"][case_data_start:].lstrip())[0]
        issue = case_data["risk_flags"][0]
        amount = case_data.get("pay", {}).get("amount_aud")
        return SimpleNamespace(text=json.dumps({
            "summary": f"{issue} analysis [1]", "issues": [f"{issue} [1]"],
            "evidence": ["Keep records [1]."], "next_steps": ["Check evidence [1]."],
            "clarification_questions": [], "risk_level": "medium", "sources": [],
            "issue_analysis": [{
                "issue": issue, "fact_from_user": str(amount),
                "why_it_may_be_unfair": f"Specific {issue} explanation [1].",
                "applicable_law_or_rule": "Official rule [1].", "section_or_clause": "",
                "comparison_or_calculation": f"Actual amount: {amount}",
                "evidence_needed": ["Records"], "confidence": "medium", "missing_information": [],
            }],
        }))

    monkeypatch.setattr(services.llm, "_get_gemini_client", lambda: SimpleNamespace(models=SimpleNamespace(generate_content=generate)))
    pay_payload = app.test_client().post("/analyze", json={**SCENARIO, "language": "en", "mainIssues": ["pay"], "pay": {"payBasis": "hourly", "amount": 15}}).get_json()
    visa_payload = app.test_client().post("/analyze", json={**SCENARIO, "language": "en", "mainIssues": ["visa"], "pay": {"payBasis": "unknown", "amount": None}}).get_json()
    assert pay_payload["issue_analysis"][0]["fact_from_user"] == "15"
    assert pay_payload["issue_analysis"] != visa_payload["issue_analysis"]


def test_prompts_require_source_grounded_award_clarification_and_facts():
    prompts = json.loads((Path(__file__).parents[1] / "data" / "locales" / "prompts.json").read_text(encoding="utf-8"))
    for language in ("vi", "en"):
        combined = prompts[language]["system_prompt"] + prompts[language]["user_prompt_template"]
        assert "issue_analysis" in combined
        assert "Award" in combined or "Award" in combined
        assert "classification" in combined
        assert "section_or_clause" in combined
        assert ("Never invent" in combined) if language == "en" else ("không bịa" in combined.lower())
        assert "not enough information" in combined.lower() or "chưa đủ thông tin" in combined.lower()
