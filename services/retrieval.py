"""Bounded Gemini tool loop for read-only pgvector knowledge retrieval."""
from __future__ import annotations

import json
import logging
import time
from typing import Any
from urllib.parse import urlparse

from google import genai
from google.genai import types

from services.config import Settings
from services.embedding_service import EmbeddingService
from services.vector_store import SQLAlchemyVectorStore

logger = logging.getLogger(__name__)
MAX_TOOL_CALLS = 8
MAX_RESULTS_PER_CALL = 6
MAX_AGENT_SECONDS = 70
MAX_PLANNING_ROUNDS = 3
AGENT_INSTRUCTION = """You are the research agent for VietRights. Examine every supplied intake field and research all materially relevant Australian workplace-rights issues. The indexed official sources are English, so use concise English search queries even when the worker wrote in Vietnamese. Group independent searches into parallel function calls in your first response to reduce latency and quota use. You may then fetch adjacent chunks or sections when context is incomplete. Never answer the worker. Never invent a URL or chunk id. Use only these read-only tools. Stop when the relevant issues have adequate evidence or the tool-call limit is near."""
QUERY_REWRITE_INSTRUCTION = "Rewrite the worker scenario as a concise English workplace-rights search query. Return only the query."


def case_to_question(case_data: dict[str, Any]) -> str:
    """Serialize all user-provided context for the research agent."""
    return json.dumps(case_data, ensure_ascii=False, separators=(",", ":"), default=str)


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
    collected: list[dict[str, Any]] = []
    started, calls_used, rounds_used = time.monotonic(), 0, 0
    config = types.GenerateContentConfig(system_instruction=AGENT_INSTRUCTION, tools=_tool_declarations(), automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True), temperature=0, max_output_tokens=500, http_options=types.HttpOptions(timeout=40000))
    chat = client.chats.create(model=settings.chat_model, config=config) if hasattr(client, "chats") else None
    pending_message: Any = contents[0]

    while calls_used < MAX_TOOL_CALLS and rounds_used < MAX_PLANNING_ROUNDS and time.monotonic() - started < MAX_AGENT_SECONDS:
        rounds_used += 1
        response = chat.send_message(pending_message) if chat else client.models.generate_content(model=settings.chat_model, contents=contents, config=config)
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
