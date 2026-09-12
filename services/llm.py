import json
import logging
import os
import re
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

GEMINI_MODEL = os.getenv("GEMINI_CHAT_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.8-flash"))
PROMPTS_FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "locales" / "prompts.json"
DEFAULT_TIMEOUT_MS = int(os.getenv("GEMINI_REQUEST_TIMEOUT_MS", "25000"))
SUPPORTED_WORKPLACE_ISSUES = {"pay", "payslip", "hours", "visa", "safety", "harassment", "other"}
SUPPORTED_PAY_BASES = {"hourly", "per_shift", "daily", "weekly", "fortnightly", "monthly", "piecework", "unknown"}
CHOICE_FIELDS = (
    "workplace", "workPattern", "paidLeave", "documentAvailability",
    "employmentTypeOnDocuments", "payslipStatus", "paymentMethod",
    "overtime", "breaks", "visaThreat", "immediateDanger", "safetyConcern", "coercion",
)


class LLMBaseError(Exception):
    """Base exception for LLM operations with safe public message and error code."""

    def __init__(self, message: str, error_code: str = "llm_error", status_code: int = 500):
        super().__init__(message)
        self.error_code = error_code
        self.status_code = status_code
        self.safe_message = message


class LLMAuthenticationError(LLMBaseError):
    """Raised when Gemini authentication fails or API key is missing/invalid."""

    def __init__(self, message: str = "Authentication failed. Please verify the configured GEMINI_API_KEY."):
        super().__init__(message, error_code="authentication_error", status_code=401)


class LLMQuotaError(LLMBaseError):
    """Raised when Gemini API rate limit or quota is exceeded."""

    def __init__(self, message: str = "API rate limit or quota exceeded. Please try again later."):
        super().__init__(message, error_code="quota_exceeded", status_code=429)


class LLMTimeoutError(LLMBaseError):
    """Raised when request to Gemini API times out."""

    def __init__(self, message: str = "The AI model request timed out. Please try again."):
        super().__init__(message, error_code="request_timeout", status_code=504)


class LLMModelNotFoundError(LLMBaseError):
    """Raised when requested Gemini model is not found or unsupported."""

    def __init__(self, message: str = "The configured Gemini model is unavailable. Please check GEMINI_MODEL."):
        super().__init__(message, error_code="model_not_found", status_code=404)


class LLMInvalidResponseError(LLMBaseError):
    """Raised when model response is malformed or violates expected schema."""

    def __init__(self, message: str = "The model returned an unexpected or malformed response."):
        super().__init__(message, error_code="invalid_model_response", status_code=502)


class LLMServiceError(LLMBaseError):
    """Raised when general upstream Gemini API or network communication fails."""

    def __init__(self, message: str = "An error occurred while communicating with the AI service."):
        super().__init__(message, error_code="service_error", status_code=502)


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
        },
        "required": [
            "summary",
            "issues",
            "evidence",
            "next_steps",
            "clarification_questions",
            "risk_level",
            "sources",
        ],
    }


def _citations_are_grounded(values: list[str], source_count: int) -> bool:
    """Require every substantive generated claim to cite a retrieved source."""
    if not values:
        return True
    if source_count < 1:
        return False
    for value in values:
        references = [int(number) for number in re.findall(r"\[(\d+)\]", value)]
        if not references or any(number < 1 or number > source_count for number in references):
            return False
    return True


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
        retrieved_context = retrieve_context(case_data)
    except errors.APIError as exc:
        if exc.code in (408, 504) or exc.status in ("DEADLINE_EXCEEDED",):
            raise LLMTimeoutError("The AI research request timed out. Please try again.") from None
        if exc.code == 429 or exc.status in ("RESOURCE_EXHAUSTED",):
            raise LLMQuotaError("API rate limit or quota exceeded. Please try again later.") from None
        raise LLMServiceError("An error occurred while researching official sources.") from None
    except (TimeoutError, httpx.TimeoutException):
        raise LLMTimeoutError() from None
    except httpx.TransportError:
        raise LLMServiceError() from None
    if not retrieved_context:
        message = (
            "Chưa tìm thấy thông tin chính thức đủ phù hợp để trả lời tình huống này. "
            "Bạn nên kiểm tra trực tiếp với Fair Work Ombudsman hoặc dịch vụ hỗ trợ pháp lý phù hợp."
            if language == "vi" else
            "No sufficiently relevant official information was found for this situation. "
            "Please check directly with the Fair Work Ombudsman or an appropriate legal support service."
        )
        return {
            "answer": message,
            "summary": message,
            "issues": [], "evidence": [], "next_steps": [], "clarification_questions": [],
            "risk_level": "medium", "sources": [],
            "content_format": "markdown",
            "retrieval": {"used": True, "result_count": 0},
        }
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

    client = _get_gemini_client()
    model_name = os.getenv("GEMINI_CHAT_MODEL", os.getenv("GEMINI_MODEL", GEMINI_MODEL))

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
    except errors.APIError as exc:
        logger.warning("Gemini API error status=%s code=%s", exc.status, exc.code)
        error_msg = str(exc).lower()
        if exc.code in (401, 403) or exc.status in ("UNAUTHENTICATED", "PERMISSION_DENIED") or "unauthenticated" in error_msg:
            raise LLMAuthenticationError("Authentication failed. Please verify the configured GEMINI_API_KEY.") from None
        if exc.code == 429 or exc.status in ("RESOURCE_EXHAUSTED",) or "quota" in error_msg:
            raise LLMQuotaError("API rate limit or quota exceeded. Please try again later.") from None
        if exc.code == 404 or exc.status in ("NOT_FOUND",) or "not found" in error_msg:
            raise LLMModelNotFoundError(f"Configured model '{model_name}' is not available. Please check GEMINI_MODEL.") from None
        if exc.code in (408, 504) or exc.status in ("DEADLINE_EXCEEDED",) or "timeout" in error_msg:
            raise LLMTimeoutError("The AI model request timed out. Please try again.") from None
        raise LLMServiceError("An error occurred while communicating with the AI service.") from None
    except TimeoutError:
        raise LLMTimeoutError("The AI model request timed out. Please try again.") from None
    except LLMBaseError:
        raise
    except Exception as exc:
        exc_str = str(exc).lower()
        if "timeout" in exc_str:
            raise LLMTimeoutError("The AI model request timed out. Please try again.") from None
        logger.error("Unexpected Gemini error type=%s", type(exc).__name__)
        raise LLMServiceError("An unexpected error occurred while communicating with the AI service.") from None

    content = getattr(response, "text", None)
    if not content:
        try:
            content = response.candidates[0].content.parts[0].text
        except Exception:
            content = ""

    if not content:
        raise LLMInvalidResponseError("Gemini returned no usable content.")

    parsed = _safe_parse_json(content)
    required = ["summary", "issues", "evidence", "next_steps", "clarification_questions", "risk_level", "sources"]
    for key in required:
        if key not in parsed:
            raise LLMInvalidResponseError(f"Missing required field in model response: {key}")

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
    }

    if result["risk_level"] not in {"low", "medium", "high"}:
        result["risk_level"] = "medium"

    claims = [result["summary"], *result["issues"], *result["next_steps"]]
    if not _citations_are_grounded([value for value in claims if value], len(source_refs)):
        raise LLMInvalidResponseError("The model response contained an unsupported or invalid citation.")

    result["sources"] = [item for item in source_refs if str(item.get("url") or "").startswith(("http://", "https://"))]
    result["answer"] = result["summary"]
    result["content_format"] = "markdown"
    result["retrieval"] = {"used": True, "result_count": len(result["sources"])}

    return result
