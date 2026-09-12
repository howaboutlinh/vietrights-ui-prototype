"""Vietnamese-to-English query rewriting and Supabase vector retrieval."""
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
QUERY_REWRITE_INSTRUCTION = """Rewrite the supplied Vietnamese or English worker scenario as one concise English search query for Australian workplace-rights documents. Preserve visa status, age, employment type, industry, location, pay rate, working hours, payslips, tax, superannuation, threats, and unsafe conditions when present. Do not answer the scenario. Return only the English search query."""

def case_to_question(case_data: dict[str, Any]) -> str:
    """Convert the existing structured intake payload into a retrieval question."""
    description = str(case_data.get("description") or "").strip()
    compact = {
        "issues": case_data.get("mainIssues"), "other_issue": case_data.get("mainIssueOther"),
        "workplace": case_data.get("workplace"), "workplace_other": case_data.get("workplaceOther"),
        "work_pattern": case_data.get("workPattern"), "pay": case_data.get("pay"),
        "payslip_status": case_data.get("payslipStatus"), "payment_method": case_data.get("paymentMethod"),
        "hours_per_week": case_data.get("hoursPerWeek"), "work_time": case_data.get("workTime"),
        "overtime": case_data.get("overtime"), "breaks": case_data.get("breaks"),
        "visa_threat": case_data.get("visaThreat"), "immediate_danger": case_data.get("immediateDanger"),
        "safety_concern": case_data.get("safetyConcern"), "coercion": case_data.get("coercion"),
    }
    facts = json.dumps({key: value for key, value in compact.items() if value not in (None, "", [], {})}, ensure_ascii=False)
    return f"{description}\nStructured worker facts: {facts}".strip()

def rewrite_search_query(question: str, settings: Settings | None = None, client: Any | None = None) -> str:
    """Translate/rewrite for retrieval, falling back to the original on any failure."""
    clean = str(question or "").strip()
    if not clean:
        return ""
    settings = settings or Settings.from_env()
    try:
        settings.validate(["gemini_api_key"])
        model_client = client or genai.Client(api_key=settings.gemini_api_key, vertexai=False)
        response = model_client.models.generate_content(
            model=settings.chat_model, contents=clean,
            config=types.GenerateContentConfig(system_instruction=QUERY_REWRITE_INSTRUCTION, temperature=0, max_output_tokens=250),
        )
        rewritten = str(getattr(response, "text", "") or "").strip()
        return rewritten or clean
    except Exception as exc:
        logger.warning("Query rewrite failed; using original text error=%s", type(exc).__name__)
        return clean

def _deduplicate(rows: list[dict[str, Any]], limit: int) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for row in sorted(rows, key=lambda item: float(item.get("similarity") or 0), reverse=True):
        fingerprint = str(row.get("content_hash") or " ".join(str(row.get("content") or "").lower().split()[:40]))
        if fingerprint in seen:
            continue
        seen.add(fingerprint)
        results.append(row)
        if len(results) >= limit:
            break
    return results

def retrieve_context(
    case_data: dict[str, Any], settings: Settings | None = None,
    embedding_service: EmbeddingService | None = None,
    vector_store: SQLAlchemyVectorStore | None = None, rewrite_client: Any | None = None,
) -> list[dict[str, Any]]:
    """Retrieve high-quality English evidence for one worker scenario."""
    settings = settings or Settings.from_env()
    query = rewrite_search_query(case_to_question(case_data), settings, rewrite_client)
    started = time.monotonic()
    embedder = embedding_service or EmbeddingService(settings)
    store = vector_store or SQLAlchemyVectorStore(settings)
    rows = store.match(embedder.embed_query(query), settings.match_threshold, settings.match_count * 2)
    rows = [row for row in rows if float(row.get("similarity") or 0) >= settings.match_threshold]
    results = _deduplicate(rows, settings.match_count)
    domains = sorted({urlparse(str(row.get("source_url") or "")).hostname or "" for row in results} - {""})
    logger.info("RAG retrieval duration_ms=%d matches=%d domains=%s", int((time.monotonic() - started) * 1000), len(results), domains)
    return results
