import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from services.retrieval import retrieve_context
from services.retry import call_with_retry, http_options
import httpx

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", os.getenv("GEMINI_CHAT_MODEL", "gemini-3.6-flash"))
PROMPTS_FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "locales" / "prompts.json"
DEFAULT_TIMEOUT_MS = int(os.getenv("GEMINI_REQUEST_TIMEOUT_MS", "25000"))
SUPPORTED_WORKPLACE_ISSUES = {"pay", "payslip", "hours", "visa", "safety", "harassment", "other"}
SUPPORTED_PAY_BASES = {"hourly", "per_shift", "daily", "weekly", "fortnightly", "monthly", "piecework", "unknown"}
TRUSTED_FALLBACK_SOURCES = [
    {"title": "Fair Work Ombudsman", "organisation": "Fair Work Ombudsman", "url": "https://www.fairwork.gov.au/"},
    {"title": "Department of Home Affairs", "organisation": "Department of Home Affairs", "url": "https://www.homeaffairs.gov.au/"},
    {"title": "SafeWork NSW", "organisation": "SafeWork NSW", "url": "https://www.safework.nsw.gov.au/"},
    {"title": "RMWC Migrant Workers Hub", "organisation": "RMWC", "url": "https://unionsnsw.org.au/your-rights/migrant-workers/"},
]
CHOICE_FIELDS = (
    "workplace", "workPattern", "paidLeave", "documentAvailability",
    "employmentTypeOnDocuments", "payslipStatus", "paymentMethod",
    "overtime", "breaks", "visaThreat", "immediateDanger", "safetyConcern", "coercion",
)


class LLMBaseError(Exception):
    """Base exception for LLM operations with safe public message and error code."""

    def __init__(self, message: str, error_code: str = "llm_error", status_code: int = 500, stage: str = "unknown"):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code
        self.safe_message = message
        self.stage = stage


class LLMAuthenticationError(LLMBaseError):
    """Raised when Gemini authentication fails or API key is missing/invalid."""

    def __init__(self, message: str = "Authentication failed. Please verify the configured GEMINI_API_KEY.", stage: str = "client_setup"):
        super().__init__(message, error_code="authentication_error", status_code=401, stage=stage)


class LLMQuotaError(LLMBaseError):
    """Raised when Gemini API rate limit or quota is exceeded."""

    def __init__(self, message: str = "API rate limit or quota exceeded. Please try again later.", stage: str = "gemini_request"):
        super().__init__(message, error_code="quota_exceeded", status_code=429, stage=stage)


class LLMTimeoutError(LLMBaseError):
    """Raised when request to Gemini API times out."""

    def __init__(self, message: str = "The AI model request timed out. Please try again.", stage: str = "gemini_request"):
        super().__init__(message, error_code="request_timeout", status_code=504, stage=stage)


class LLMModelNotFoundError(LLMBaseError):
    """Raised when requested Gemini model is not found or unsupported."""

    def __init__(self, message: str = "The configured Gemini model is unavailable. Please check GEMINI_MODEL."):
        super().__init__(message, error_code="model_not_found", status_code=404)


class LLMInvalidResponseError(LLMBaseError):
    """Raised when model response is malformed or violates expected schema."""

    def __init__(self, message: str = "The model returned an unexpected or malformed response.", stage: str = "response_parsing"):
        super().__init__(message, error_code="invalid_model_response", status_code=502, stage=stage)


class LLMServiceError(LLMBaseError):
    """Raised when general upstream Gemini API or network communication fails."""

    def __init__(self, message: str = "An error occurred while communicating with the AI service.", stage: str = "gemini_request"):
        super().__init__(message, error_code="service_error", status_code=502, stage=stage)


def _coerce_list(value: Any) -> List[str]:
    """Coerce input value into a clean list of non-empty strings."""
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value).strip()] if str(value).strip() else []


def _safe_parse_json(raw_response: str) -> Dict[str, Any]:
    """Parse JSON payload from model response with markdown code block stripping."""
    text = str(raw_response or "").strip()
    if not text:
        raise LLMInvalidResponseError("Gemini returned an empty response.")

    if text.startswith("```"):
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:].strip()

    try:
        return json.loads(text)
    except json.JSONDecodeError:
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            try:
                return json.loads(text[start:end + 1])
            except json.JSONDecodeError:
                pass
        raise LLMInvalidResponseError("Gemini response was not valid JSON.")


def _load_prompt_templates() -> Dict[str, Dict[str, str]]:
    """Load localization prompt templates from the UTF-8 JSON resource file."""
    if not PROMPTS_FILE_PATH.exists():
        raise FileNotFoundError(f"Prompt template file not found: {PROMPTS_FILE_PATH}")

    with PROMPTS_FILE_PATH.open("r", encoding="utf-8") as file_handle:
        return json.load(file_handle)


def _format_context_for_prompt(context_entries: List[Dict[str, Any]]) -> str:
    """Format retrieved official context entries into a structured text block for the prompt."""
    if not context_entries:
        return (
            "No matching official knowledge source was found. "
            "Use only cautious general guidance and clearly say when the answer is not grounded in an official source."
        )

    blocks = []
    for number, entry in enumerate(context_entries, start=1):
        title = str(entry.get("document_title") or "Untitled source").strip()
        organisation = str(entry.get("source_name") or "Unknown organisation").strip()
        section = str(entry.get("section_title") or "").strip()
        source_url = str(entry.get("source_url") or "").strip()
        content = str(entry.get("content") or "").strip()

        block = (
            f"[SOURCE {number}]\n"
            f"  Title: {title}\n"
            f"  Organisation: {organisation}\n"
            f"  Section: {section or 'Not specified'}\n"
            f"  Source URL: {source_url or 'URL not provided'}\n"
            f"  Evidence: {content}"
        )
        blocks.append(block)

    return "\n\n".join(blocks)


def _get_gemini_client() -> genai.Client:
    """Initialize and return the Google GenAI client configured for Gemini Developer API."""
    api_key = os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")
    if not api_key:
        raise LLMAuthenticationError("Missing GEMINI_API_KEY environment variable.")

    # Explicitly force vertexai=False to avoid Vertex AI / OAuth collisions
    return genai.Client(api_key=api_key, vertexai=False)


def _response_schema() -> Dict[str, Any]:
    """Define the structured JSON schema for case analysis output."""
    return {
        "type": "object",
        "properties": {
            "summary": {"type": "string"},
            "issues": {"type": "array", "items": {"type": "string"}},
            "evidence": {"type": "array", "items": {"type": "string"}},
            "next_steps": {"type": "array", "items": {"type": "string"}},
            "clarification_questions": {"type": "array", "items": {"type": "string"}},
            "risk_level": {"type": "string", "enum": ["low", "medium", "high"]},
            "sources": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "organisation": {"type": "string"},
                        "url": {"type": "string"},
                    },
                    "required": ["title", "organisation", "url"],
                },
            },
            "issue_analysis": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "issue": {"type": "string"},
                        "fact_from_user": {"type": "string"},
                        "why_it_may_be_unfair": {"type": "string"},
                        "applicable_law_or_rule": {"type": "string"},
                        "section_or_clause": {"type": "string"},
                        "comparison_or_calculation": {"type": "string"},
                        "evidence_needed": {"type": "array", "items": {"type": "string"}},
                        "confidence": {"type": "string"},
                        "missing_information": {"type": "array", "items": {"type": "string"}},
                    },
                    "required": ["issue", "fact_from_user", "why_it_may_be_unfair", "applicable_law_or_rule", "section_or_clause", "comparison_or_calculation", "evidence_needed", "confidence", "missing_information"],
                },
            },
        },
        "required": [
            "summary",
            "issues",
            "evidence",
            "next_steps",
            "clarification_questions",
            "risk_level",
            "sources",
            "issue_analysis",
        ],
    }



def _fallback_response(case_data: Dict[str, Any], retrieved_context: List[Dict[str, Any]], language: str, reason: str) -> Dict[str, Any]:
    """Return cautious, deterministic guidance when Gemini cannot respond."""
    issues = {str(issue).strip() for issue in case_data.get("mainIssues") or []}
    has_sources = bool(retrieved_context)
    source_refs = [
        {
            "number": number,
            "title": item.get("document_title") or item.get("source_name") or "Official source",
            "section": item.get("section_title"),
            "source_name": item.get("source_name"),
            "organisation": item.get("source_name"),
            "url": item.get("source_url"),
        }
        for number, item in enumerate(retrieved_context, start=1)
        if str(item.get("source_url") or "").startswith(("http://", "https://"))
    ]
    sources = source_refs if retrieved_context else TRUSTED_FALLBACK_SOURCES
    citation = " [1]" if source_refs else ""

    if language == "vi":
        summary = "Dưới đây là hướng dẫn thận trọng dựa trên thông tin bạn đã cung cấp và các nguồn chính thức hiện có."
        issue_rules = {
            "pay": f"Kiểm tra mức lương tối thiểu và giữ lại hồ sơ tiền lương, lịch làm việc và thanh toán.{citation}",
            "payslip": f"Kiểm tra yêu cầu về payslip và giữ bản payslip, tin nhắn, lịch làm việc cùng bằng chứng thanh toán.{citation}",
            "hours": f"Ghi lại ca làm, thời gian nghỉ và giờ làm thêm; giữ roster hoặc tin nhắn liên quan.{citation}",
            "visa": f"Tình trạng visa không làm mất quyền tại nơi làm việc. Hãy tìm hỗ trợ phù hợp nếu bị đe dọa liên quan đến visa.{citation}",
            "safety": "Nếu đang nguy hiểm ngay lập tức, gọi 000. Với vấn đề an toàn không khẩn cấp, liên hệ SafeWork NSW.",
            "harassment": f"Giữ tin nhắn, roster và hồ sơ thanh toán; tìm dịch vụ hỗ trợ phù hợp.{citation}",
            "other": "Ghi lại sự việc, giữ các tài liệu liên quan và tìm hỗ trợ phù hợp.",
        }
        issues_text = [issue_rules[issue] for issue in issues if issue in issue_rules]
        evidence = ["Giữ payslip, roster, tin nhắn, hồ sơ thanh toán và ghi chú về các sự việc liên quan."]
        next_steps = ["Kiểm tra các nguồn chính thức bên dưới và tìm hỗ trợ phù hợp với tình huống của bạn."]
        questions = ["Bạn có tài liệu hoặc bằng chứng nào khác liên quan đến tình huống này không?"]
    else:
        summary = "The following is cautious guidance based on the information provided and the official sources currently available."
        issue_rules = {
            "pay": f"Check minimum pay and keep wage, roster and payment records.{citation}",
            "payslip": f"Check payslip requirements and keep payslips, messages, rosters and payment evidence.{citation}",
            "hours": f"Record shifts, breaks and overtime, and keep rosters or related messages.{citation}",
            "visa": f"Visa status does not remove workplace rights. Seek appropriate support if you face visa-related threats.{citation}",
            "safety": "If you are in immediate danger, call 000. For non-urgent workplace safety concerns, contact SafeWork NSW.",
            "harassment": f"Preserve messages, rosters and payment records, and seek appropriate support.{citation}",
            "other": "Record what happened, preserve relevant documents, and seek appropriate support.",
        }
        issues_text = [issue_rules[issue] for issue in issues if issue in issue_rules]
        evidence = ["Keep payslips, rosters, messages, payment records and notes about relevant events."]
        next_steps = ["Review the official sources below and seek support appropriate to your situation."]
        questions = ["Do you have other documents or evidence related to this situation?"]

    issue_analysis = [
        {
            "issue": issue,
            "fact_from_user": str(case_data.get("description") or "").strip() or "Dữ kiện chi tiết chưa được cung cấp.",
            "why_it_may_be_unfair": text,
            "applicable_law_or_rule": "Chưa xác định từ nguồn dự phòng; cần kiểm tra nguồn chính thức.",
            "section_or_clause": "",
            "comparison_or_calculation": "",
            "evidence_needed": evidence,
            "confidence": "low",
            "missing_information": questions,
        }
        for issue, text in zip(issues, issues_text)
    ]

    return {
        "answer": summary,
        "summary": summary,
        "ai_used": False,
        "issues": issues_text,
        "evidence": evidence,
        "next_steps": next_steps,
        "clarification_questions": questions,
        "issue_analysis": issue_analysis,
        "risk_level": "high" if "safety" in issues else "medium",
        "sources": sources,
        "content_format": "markdown",
        "retrieval": {"used": True, "result_count": len(source_refs)},
        "fallback": True,
        "fallback_reason": reason,
    }


def analyze_case(case_data: Dict[str, Any]) -> Dict[str, Any]:
    """Analyze a workplace rights case using retrieved context and Gemini LLM."""
    if not isinstance(case_data, dict):
        raise ValueError("Case data must be a dictionary.")

    main_issues = case_data.get("mainIssues")
    if not isinstance(main_issues, list) or not main_issues:
        raise ValueError("Case data must include a non-empty 'mainIssues' list.")

    clean_issues = []
    for issue in main_issues:
        if not isinstance(issue, str) or issue.strip() not in SUPPORTED_WORKPLACE_ISSUES:
            raise ValueError(f"Invalid workplace issue value: {issue}")
        clean_issues.append(issue.strip())

    if "other" in clean_issues:
        other_description = str(case_data.get("mainIssueOther") or "").strip()
        if not other_description:
            raise ValueError("Description for 'other' issue must be provided when 'other' is selected.")

    for field in CHOICE_FIELDS:
        value = case_data.get(field)
        if field in case_data and (value is None or (isinstance(value, str) and not value.strip())):
            raise ValueError(f"'{field}' cannot be empty.")

    pay_info = case_data.get("pay")
    if pay_info is not None:
        if not isinstance(pay_info, dict):
            raise ValueError("'pay' field must be a dictionary if provided.")
        pay_basis = pay_info.get("payBasis")
        if "payBasis" in pay_info and (not isinstance(pay_basis, str) or not pay_basis.strip() or pay_basis.strip() not in SUPPORTED_PAY_BASES):
            raise ValueError(f"Invalid pay basis value: {pay_basis}")

    language = str(case_data.get("language") or "vi").lower()
    if language not in {"vi", "en"}:
        language = "vi"

    try:
        client = _get_gemini_client()
    except LLMAuthenticationError:
        logger.exception("Gemini analysis failed stage=client_setup")
        raise

    try:
        retrieved_context = retrieve_context(case_data)
    except errors.APIError as exc:
        if exc.code in (408, 504) or exc.status in ("DEADLINE_EXCEEDED",):
            raise LLMTimeoutError(stage="gemini_request") from exc
        if exc.code == 429 or exc.status in ("RESOURCE_EXHAUSTED",):
            raise LLMQuotaError(stage="gemini_request") from exc
        raise LLMServiceError(stage="gemini_request") from exc
    except (TimeoutError, httpx.TimeoutException) as exc:
        raise LLMTimeoutError(stage="gemini_request") from exc
    except httpx.TransportError:
        raise LLMServiceError(stage="gemini_request") from exc
    except LLMBaseError as exc:
        raise
    formatted_context = _format_context_for_prompt(retrieved_context)
    source_refs = [
        {
            "number": number,
            "title": item.get("document_title"),
            "section": item.get("section_title"),
            "source_name": item.get("source_name"),
            "organisation": item.get("source_name"),
            "url": item.get("source_url"),
            "similarity": round(float(item.get("similarity") or 0), 4),
        }
        for number, item in enumerate(retrieved_context, start=1)
        if item.get("source_url")
    ]

    prompt_templates = _load_prompt_templates()
    lang_prompts = prompt_templates.get(language) or prompt_templates.get("vi")
    if not lang_prompts:
        raise LLMInvalidResponseError(f"Prompt template for language '{language}' not found in prompts resource.")

    system_prompt = lang_prompts["system_prompt"]
    case_data_json = json.dumps(case_data, ensure_ascii=False)
    user_prompt = lang_prompts["user_prompt_template"].format(
        case_data_json=case_data_json,
        formatted_context=formatted_context
    )

    model_name = os.getenv("GEMINI_MODEL", os.getenv("GEMINI_CHAT_MODEL", GEMINI_MODEL))
    logger.info("Starting Gemini analysis model=%s", model_name)

    try:
        response = call_with_retry(lambda timeout_ms: client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                response_mime_type="application/json",
                response_schema=_response_schema(),
                http_options=http_options(timeout_ms),
            ),
        ), label='answer')
    except LLMAuthenticationError:
        logger.exception("Gemini analysis failed stage=client_setup")
        raise
    except errors.APIError as exc:
        logger.exception("Gemini analysis failed stage=api_request")
        logger.warning("Gemini API error status=%s code=%s", exc.status, exc.code)
        error_msg = str(exc).lower()
        if exc.code in (401, 403) or exc.status in ("UNAUTHENTICATED", "PERMISSION_DENIED") or "unauthenticated" in error_msg:
            raise LLMAuthenticationError("Authentication failed. Please verify the configured GEMINI_API_KEY.") from None
        if exc.code == 429 or exc.status in ("RESOURCE_EXHAUSTED",) or "quota" in error_msg:
            raise LLMQuotaError(stage="gemini_request") from exc
        if exc.code == 404 or exc.status in ("NOT_FOUND",) or "not found" in error_msg:
            raise LLMModelNotFoundError(f"Configured model '{model_name}' is not available. Please check GEMINI_MODEL.") from None
        if exc.code in (408, 504) or exc.status in ("DEADLINE_EXCEEDED",) or "timeout" in error_msg:
            raise LLMTimeoutError(stage="gemini_request") from exc
        raise LLMServiceError(stage="gemini_request") from exc
    except TimeoutError:
        logger.exception("Gemini analysis failed stage=api_request")
        raise LLMTimeoutError(stage="gemini_request") from exc
    except (LLMQuotaError, LLMTimeoutError, LLMServiceError) as exc:
        logger.exception("Gemini analysis failed stage=api_request")
        raise
    except Exception as exc:
        logger.exception("Gemini analysis failed stage=api_request")
        exc_str = str(exc).lower()
        if "timeout" in exc_str:
            raise LLMTimeoutError(stage="gemini_request") from exc
        logger.error("Unexpected Gemini error type=%s", type(exc).__name__)
        raise LLMServiceError(stage="gemini_request") from exc

    content = getattr(response, "text", None)
    if not content:
        try:
            content = response.candidates[0].content.parts[0].text
        except Exception:
            logger.exception("Gemini analysis failed stage=response_parsing")
            content = ""

    if not content:
        logger.error("Gemini analysis failed stage=response_parsing reason=empty_response")
        raise LLMInvalidResponseError(stage="response_parsing") from None

    try:
        parsed = _safe_parse_json(content)
    except LLMInvalidResponseError:
        logger.exception("Gemini analysis failed stage=response_parsing")
        raise LLMInvalidResponseError(stage="response_parsing") from None
    required = ["summary", "issues", "evidence", "next_steps", "clarification_questions", "risk_level", "sources", "issue_analysis"]
    for key in required:
        if key not in parsed:
            logger.exception("Gemini analysis failed stage=schema_validation")
            raise LLMInvalidResponseError(stage="schema_validation") from None

    result = {
        "summary": str(parsed.get("summary", "")).strip(),
        "issues": _coerce_list(parsed.get("issues", [])),
        "evidence": _coerce_list(parsed.get("evidence", [])),
        "next_steps": _coerce_list(parsed.get("next_steps", [])),
        "clarification_questions": _coerce_list(parsed.get("clarification_questions", [])),
        "risk_level": str(parsed.get("risk_level", "low")).strip().lower(),
        "sources": [
            {
                "title": str(item.get("title", "")).strip(),
                "organisation": str(item.get("organisation", "")).strip(),
                "url": str(item.get("url", "")).strip(),
            }
            for item in (parsed.get("sources") or [])
            if isinstance(item, dict)
        ],
        "issue_analysis": [
            {
                "issue": str(item.get("issue", "")).strip(),
                "fact_from_user": str(item.get("fact_from_user", "")).strip(),
                "why_it_may_be_unfair": str(item.get("why_it_may_be_unfair", "")).strip(),
                "applicable_law_or_rule": str(item.get("applicable_law_or_rule", "")).strip(),
                "section_or_clause": str(item.get("section_or_clause", "")).strip(),
                "comparison_or_calculation": str(item.get("comparison_or_calculation", "")).strip(),
                "evidence_needed": _coerce_list(item.get("evidence_needed", [])),
                "confidence": str(item.get("confidence", "low")).strip(),
                "missing_information": _coerce_list(item.get("missing_information", [])),
            }
            for item in (parsed.get("issue_analysis") or []) if isinstance(item, dict)
        ],
    }

    if result["risk_level"] not in {"low", "medium", "high"}:
        result["risk_level"] = "medium"

    result["sources"] = [item for item in source_refs if str(item.get("url") or "").startswith(("http://", "https://"))]
    result["answer"] = result["summary"]
    result["ai_used"] = True
    result["fallback"] = False
    result["content_format"] = "markdown"
    result["retrieval"] = {"used": True, "result_count": len(result["sources"])}

    logger.info("Gemini analysis succeeded model=%s", model_name)

    return result
