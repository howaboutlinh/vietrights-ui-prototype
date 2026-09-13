"""Bounded Gemini tool loop for read-only pgvector knowledge retrieval."""
from __future__ import annotations

import json
import logging
import time
import hashlib
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from google import genai
from google.genai import types

from services.config import Settings
from services.embedding_service import EmbeddingService
from services.vector_store import SQLAlchemyVectorStore
from services.retry import call_with_retry, http_options

logger = logging.getLogger(__name__)
LOCAL_KNOWLEDGE_ROOT = Path(__file__).resolve().parents[1] / "data" / "knowledge"
MAX_TOOL_CALLS = 8
MAX_RESULTS_PER_CALL = 6
MAX_AGENT_SECONDS = 70
MAX_PLANNING_ROUNDS = 3
AGENT_INSTRUCTION = """You are the research agent for VietRights. Examine every supplied intake field and research all materially relevant Australian workplace-rights issues. The indexed official sources are English, so use concise English search queries even when the worker wrote in Vietnamese. Group independent searches into parallel function calls in your first response to reduce latency and quota use. You may then fetch adjacent chunks or sections when context is incomplete. Never answer the worker. Never invent a URL or chunk id. Use only these read-only tools. Stop when the relevant issues have adequate evidence or the tool-call limit is near."""
QUERY_REWRITE_INSTRUCTION = "Rewrite the worker scenario as a concise English workplace-rights search query. Return only the query."


def compact_case_data(case_data: dict[str, Any]) -> dict[str, Any]:
    """Build a small, privacy-conscious worker-case object without inference."""
    compact: dict[str, Any] = {}

    def add(key: str, value: Any) -> None:
        if value is not None and value != "" and value != [] and value != {}:
            compact[key] = value

    add("language", case_data.get("language"))
    description = str(case_data.get("description") or "").strip()[:2000]
    issues = list(dict.fromkeys(str(issue).strip() for issue in case_data.get("mainIssues") or [] if str(issue).strip()))
    scenario = description or ", ".join(issues)
    add("issue", scenario[:2000])
    employment = case_data.get("employmentTypeOnDocuments")
    add("employment", [employment] if employment not in (None, "", "unknown") else None)

    has_contract = case_data.get("has_contract")
    has_payslip = case_data.get("has_payslip")
    if has_contract is None and has_payslip is None:
        document_value = case_data.get("documentAvailability")
        document_status = {
            "both": (True, True), "payslip_only": (False, True),
            "contract_only": (True, False), "neither": (False, False), "unsure": (None, None),
        }.get(document_value, (None, None))
        has_contract, has_payslip = document_status
    add("contract", "yes" if has_contract is True else "no" if has_contract is False else "unknown")
    add("payslip", "yes" if has_payslip is True else "no" if has_payslip is False else "unknown")

    pay = case_data.get("pay") or {}
    if isinstance(pay, dict):
        compact_pay = {}
        add_method = pay.get("payBasis")
        if add_method not in (None, ""):
            compact_pay["method"] = add_method
        if pay.get("amount") is not None:
            compact_pay["amount_aud"] = pay["amount"]
        if compact_pay:
            compact["pay"] = compact_pay

    schedule = {}
    if case_data.get("hoursPerWeek") is not None:
        schedule["hours_per_week"] = case_data["hoursPerWeek"]
    if case_data.get("hoursPerShift") is not None:
        schedule["hours_per_shift"] = case_data["hoursPerShift"]
    work_time = {str(value).strip() for value in case_data.get("workTime") or []}
    for name, marker in (("night", "night"), ("weekend", "weekend"), ("public_holiday", "public_holiday")):
        if marker in work_time:
            schedule[name] = True
    if work_time:
        schedule["work_time"] = sorted(work_time)
    if schedule:
        compact["schedule"] = schedule

    flags = issues + [str(case_data.get("overtime")).strip()] if case_data.get("overtime") not in (None, "", "unknown") else issues
    add("risk_flags", list(dict.fromkeys(flag for flag in flags if flag)))
    for key in ("workplace", "workPattern", "payslipStatus", "paymentMethod", "paidLeave", "visaThreat", "safetyConcern", "coercion"):
        value = case_data.get(key)
        if value not in (None, ""):
            compact[key] = value
    return compact


def load_local_knowledge(root: str | Path = LOCAL_KNOWLEDGE_ROOT) -> list[dict[str, Any]]:
    """Load normalized JSON source records recursively; empty folders are valid."""
    root_path = Path(root)
    if not root_path.is_dir():
        return []
    records: list[dict[str, Any]] = []
    for path in sorted(root_path.rglob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            logger.warning("Local knowledge file skipped name=%s error=%s", path.name, type(exc).__name__)
            continue
        values = payload if isinstance(payload, list) else [payload]
        for record in values:
            if not isinstance(record, dict) or not record.get("content"):
                continue
            if "TODO" in str(record.get("source_url") or "") or any("TODO" in str(item) for item in record["content"]):
                continue
            text = " ".join(str(item).strip() for item in record["content"] if str(item).strip())
            source_url = str(record.get("source_url") or "")
            records.append({
                "id": str(path.relative_to(root_path)),
                "content_hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
                "source_name": record.get("organisation"),
                "source_url": source_url,
                "document_title": record.get("title"),
                "section_title": record.get("topic"),
                "document_type": "json",
                "content": text,
                "similarity": 0.61,
            })
    return records


def case_to_question(case_data: dict[str, Any]) -> str:
    """Serialize the compact user case for the research agent."""
    compact_case = compact_case_data(case_data)
    return json.dumps(compact_case, ensure_ascii=False, separators=(",", ":"))


def rewrite_search_query(question: str, settings: Settings | None = None, client: Any | None = None) -> str:
    """Backward-compatible standalone query rewrite helper."""
    clean = str(question or "").strip()
    if not clean:
        return ""
    settings = settings or Settings.from_env()
    try:
        settings.validate(["gemini_api_key"])
        model_client = client or genai.Client(api_key=settings.gemini_api_key, vertexai=False)
        response = model_client.models.generate_content(
            model=settings.chat_model,
            contents=clean,
            config=types.GenerateContentConfig(
                system_instruction=QUERY_REWRITE_INSTRUCTION, temperature=0, max_output_tokens=250
            ),
        )
        return str(getattr(response, "text", "") or "").strip() or clean
    except Exception as exc:
        logger.warning("Query rewrite failed; using original text error=%s", type(exc).__name__)
        return clean


def _tool_declarations() -> list[types.Tool]:
    declarations = [
        types.FunctionDeclaration(name="search_knowledge", description="Semantic search of official workplace-rights chunks. Use a focused English query.", parameters={"type": "object", "properties": {"query": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 6}}, "required": ["query"]}),
        types.FunctionDeclaration(name="search_knowledge_by_topic", description="Semantic search focused on one or more rights topics.", parameters={"type": "object", "properties": {"query": {"type": "string"}, "topics": {"type": "array", "items": {"type": "string"}}, "limit": {"type": "integer", "minimum": 1, "maximum": 6}}, "required": ["query", "topics"]}),
        types.FunctionDeclaration(name="get_chunk_context", description="Get nearby chunks after semantic search when a passage is incomplete.", parameters={"type": "object", "properties": {"chunk_id": {"type": "integer"}, "radius": {"type": "integer", "minimum": 0, "maximum": 2}}, "required": ["chunk_id"]}),
        types.FunctionDeclaration(name="get_source_sections", description="Get matching sections from a source URL already returned by another tool.", parameters={"type": "object", "properties": {"source_url": {"type": "string"}, "section": {"type": "string"}, "limit": {"type": "integer", "minimum": 1, "maximum": 6}}, "required": ["source_url"]}),
    ]
    return [types.Tool(function_declarations=declarations)]


def _deduplicate(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    results, seen = [], set()
    for row in sorted(rows, key=lambda item: float(item.get("similarity") or 0), reverse=True):
        fingerprint = str(row.get("content_hash") or row.get("id") or "")
        if not fingerprint or fingerprint in seen:
            continue
        seen.add(fingerprint)
        results.append(row)
        if len(results) >= limit:
            break
    return results


class KnowledgeTools:
    """Validated read-only operations exposed to the model."""

    def __init__(self, settings: Settings, embedder=None, store=None):
        self.settings = settings
        self.embedder = embedder or EmbeddingService(settings)
        self.store = store or SQLAlchemyVectorStore(settings)
        self.allowed_urls: set[str] = set()

    def _search(self, query: str, limit: int) -> list[dict[str, Any]]:
        query = str(query or "").strip()[:1000]
        if not query:
            return []
        limit = min(max(int(limit or self.settings.match_count), 1), MAX_RESULTS_PER_CALL)
        rows = self.store.match(self.embedder.embed_query(query), self.settings.match_threshold, limit)
        self.allowed_urls.update(str(row.get("source_url") or "") for row in rows)
        return rows

    def call(self, name: str, arguments: dict[str, Any]) -> list[dict[str, Any]]:
        if name == "search_knowledge":
            return self._search(arguments.get("query", ""), arguments.get("limit", self.settings.match_count))
        if name == "search_knowledge_by_topic":
            topics = [str(value).strip()[:80] for value in arguments.get("topics", [])[:6] if str(value).strip()]
            query = f"{arguments.get('query', '')} Topics: {', '.join(topics)}"
            return self._search(query, arguments.get("limit", self.settings.match_count))
        if name == "get_chunk_context":
            return self.store.surrounding_chunks(int(arguments.get("chunk_id", 0)), arguments.get("radius", 1))
        if name == "get_source_sections":
            source_url = str(arguments.get("source_url") or "")
            if source_url not in self.allowed_urls:
                return []
            return self.store.source_sections(source_url, arguments.get("section", ""), arguments.get("limit", 4))
        return []


def _serializable_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    keys = ("id", "source_name", "source_url", "document_title", "document_type", "section_title", "content", "content_hash", "chunk_index", "similarity")
    return [{key: row.get(key) for key in keys if row.get(key) is not None} for row in rows]


def retrieve_context(case_data: dict[str, Any], settings: Settings | None = None, embedding_service=None, vector_store=None, rewrite_client=None) -> list[dict[str, Any]]:
    """Let Gemini call bounded retrieval tools and return deduplicated evidence."""
    settings = settings or Settings.from_env()
    settings.validate(["gemini_api_key", "database_url"])
    client = rewrite_client or genai.Client(api_key=settings.gemini_api_key, vertexai=False)
    knowledge_tools = KnowledgeTools(settings, embedding_service, vector_store)
    contents: list[Any] = [f"Research this complete worker intake:\n{case_to_question(case_data)}"]
    collected: list[dict[str, Any]] = load_local_knowledge() if vector_store is None else []
    started, calls_used, rounds_used = time.monotonic(), 0, 0
    config = types.GenerateContentConfig(system_instruction=AGENT_INSTRUCTION, tools=_tool_declarations(), automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True), temperature=0, max_output_tokens=500, http_options=types.HttpOptions(timeout=40000))
    chat = client.chats.create(model=settings.chat_model, config=config) if hasattr(client, "chats") else None
    pending_message: Any = contents[0]

    while calls_used < MAX_TOOL_CALLS and rounds_used < MAX_PLANNING_ROUNDS and time.monotonic() - started < MAX_AGENT_SECONDS:
        rounds_used += 1
        def plan(timeout_ms):
            attempt_config = config.model_copy(update={'http_options': http_options(timeout_ms)})
            return chat.send_message(pending_message, config=attempt_config) if chat else client.models.generate_content(model=settings.chat_model, contents=contents, config=attempt_config)
        response = call_with_retry(plan, label='research', deadline=started + MAX_AGENT_SECONDS)
        function_calls = list(getattr(response, "function_calls", None) or [])
        if not function_calls:
            break
        candidates = getattr(response, "candidates", None) or []
        candidate_content = getattr(candidates[0], "content", None) if candidates else None
        if candidate_content is not None:
            contents.append(candidate_content)
        response_parts = []
        for function_call in function_calls:
            if calls_used >= MAX_TOOL_CALLS:
                break
            name = str(getattr(function_call, "name", ""))
            arguments = dict(getattr(function_call, "args", {}) or {})
            rows = knowledge_tools.call(name, arguments)
            collected.extend(rows)
            calls_used += 1
            response_parts.append(types.Part.from_function_response(name=name, response={"results": _serializable_rows(rows), "result_count": len(rows)}))
        if not response_parts:
            break
        if chat:
            pending_message = response_parts
        else:
            # Gemini Developer API expects function responses in a USER turn.
            contents.append(types.Content(role="user", parts=response_parts))

    results = _deduplicate(collected, min(settings.match_count * 2, 12))
    domains = sorted({urlparse(str(row.get("source_url") or "")).hostname or "" for row in results} - {""})
    logger.info("Agentic retrieval duration_ms=%d planning_rounds=%d tool_calls=%d matches=%d domains=%s", int((time.monotonic() - started) * 1000), rounds_used, calls_used, len(results), domains)
    return results
