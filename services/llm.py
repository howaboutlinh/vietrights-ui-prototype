import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import errors, types

from services.retrieval import retrieve_context

load_dotenv()

logger = logging.getLogger(__name__)

GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-3.6-flash")
PROMPTS_FILE_PATH = Path(__file__).resolve().parents[1] / "data" / "locales" / "prompts.json"
DEFAULT_TIMEOUT_MS = int(os.getenv("GEMINI_REQUEST_TIMEOUT_MS", "25000"))
SUPPORTED_WORKPLACE_ISSUES = {"pay", "payslip", "hours", "visa", "safety", "harassment", "other"}
SUPPORTED_PAY_BASES = {"hourly", "per_shift", "daily", "weekly", "fortnightly", "monthly", "piecework", "unknown"}


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
    for entry in context_entries:
        title = str(entry.get("title") or "Untitled source").strip()
        organisation = str(entry.get("organisation") or "Unknown organisation").strip()
        topic = str(entry.get("topic") or "general").strip()
        source_url = str(entry.get("source_url") or "").strip()
        content = entry.get("relevant_content") or entry.get("content") or []

        if isinstance(content, list):
            content_items = [str(item).strip() for item in content if str(item).strip()]
        else:
            content_items = [str(content).strip()] if str(content).strip() else []

        block = (
            f"- Title: {title}\n"
            f"  Organisation: {organisation}\n"
            f"  Topic: {topic}\n"
            f"  Source URL: {source_url or 'URL not provided'}\n"
            f"  Content:\n"
            + ("\n".join(f"    * {item}" for item in content_items) if content_items else "    * No extracted content available yet.")
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

    pay_info = case_data.get("pay")
    if pay_info is not None:
        if not isinstance(pay_info, dict):
            raise ValueError("'pay' field must be a dictionary if provided.")
        pay_basis = pay_info.get("payBasis")
        if pay_basis is not None and (not isinstance(pay_basis, str) or pay_basis.strip() not in SUPPORTED_PAY_BASES):
            raise ValueError(f"Invalid pay basis value: {pay_basis}")

    language = str(case_data.get("language") or "vi").lower()
    if language not in {"vi", "en"}:
        language = "vi"

    retrieved_context = retrieve_context(case_data, top_k=5)
    formatted_context = _format_context_for_prompt(retrieved_context)
    source_refs = [
        {
            "title": item.get("title"),
            "organisation": item.get("organisation"),
            "url": item.get("source_url"),
        }
        for item in retrieved_context
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
    model_name = os.getenv("GEMINI_MODEL", GEMINI_MODEL)

    try:
        response = client.models.generate_content(
            model=model_name,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=system_prompt,
                temperature=0.3,
                response_mime_type="application/json",
                response_schema=_response_schema(),
                http_options=types.HttpOptions(timeout=DEFAULT_TIMEOUT_MS),
            ),
        )
    except errors.APIError as exc:
        logger.warning("Gemini API error status=%s code=%s: %s", exc.status, exc.code, exc.message)
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
        logger.error("Unexpected error during Gemini content generation: %s", exc, exc_info=True)
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

    if source_refs:
        valid_sources = []
        for item in source_refs:
            if item.get("title") or item.get("organisation") or item.get("url"):
                url = str(item.get("url") or "").strip()
                valid_sources.append({
                    "title": str(item.get("title") or "Official source").strip(),
                    "organisation": str(item.get("organisation") or "Official organisation").strip(),
                    "url": url if url.startswith(("http://", "https://")) else "",
                })
        result["sources"] = valid_sources
    else:
        sanitized_sources = []
        for item in result.get("sources", []):
            if isinstance(item, dict) and (item.get("title") or item.get("organisation")):
                url = str(item.get("url") or "").strip()
                sanitized_sources.append({
                    "title": str(item.get("title") or "Official source").strip(),
                    "organisation": str(item.get("organisation") or "Official organisation").strip(),
                    "url": url if url.startswith(("http://", "https://")) else "",
                })
        result["sources"] = sanitized_sources

    return result
