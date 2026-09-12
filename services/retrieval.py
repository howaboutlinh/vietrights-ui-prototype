import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List


BASE_DIR = Path(__file__).resolve().parents[1]
KNOWLEDGE_DIR = BASE_DIR / "data" / "knowledge"


TOPIC_KEYWORDS = {
    "pay": ["pay", "wage", "underpayment", "low pay", "hourly pay", "minimum pay", "fortnightly", "fortnight", "weekly pay"],
    "payslip": ["payslip", "pay slip", "salary slip", "payment record"],
    "overtime": ["overtime", "extra hours", "long hours", "hours worked"],
    "hours_and_breaks": ["hours", "break", "rest break", "meal break", "weekend work"],
    "casual_employment": ["casual", "casual employment", "casual worker", "on-call"],
    "visa_and_migrant_rights": ["visa", "migrant worker", "work rights", "migration", "visa threat"],
    "workplace_safety": ["safety", "safe work", "unsafe", "injury", "hazard"],
}


def _normalise_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).lower()
    text = re.sub(r"[^a-z0-9\s]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def _flatten_case_values(value: Any) -> List[str]:
    values: List[str] = []

    if isinstance(value, dict):
        for item in value.values():
            values.extend(_flatten_case_values(item))
    elif isinstance(value, list):
        for item in value:
            values.extend(_flatten_case_values(item))
    elif isinstance(value, (str, int, float, bool)):
        text = str(value).strip()
        if text:
            values.append(text)

    return values


def _build_search_text(case_data: Dict[str, Any]) -> str:
    parts: List[str] = []
    for item in _flatten_case_values(case_data):
        parts.append(_normalise_text(item))
    return " ".join(part for part in parts if part)


def _load_knowledge_entries() -> List[Dict[str, Any]]:
    entries: List[Dict[str, Any]] = []
    if not KNOWLEDGE_DIR.exists():
        return entries

    for path in sorted(KNOWLEDGE_DIR.rglob("*.json")):
        try:
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
        except (json.JSONDecodeError, OSError):
            continue

        if not isinstance(payload, dict):
            continue

        content = payload.get("content") or []
        if not isinstance(content, list):
            content = [str(content)]

        entry_text = " ".join(str(item) for item in content if item is not None)
        entries.append({
            "title": payload.get("title", path.stem),
            "organisation": payload.get("organisation", "Unknown"),
            "topic": payload.get("topic", "general"),
            "source_url": payload.get("source_url", ""),
            "content": content,
            "_text": _normalise_text(" ".join([payload.get("title", ""), payload.get("topic", ""), payload.get("organisation", ""), entry_text]))
        })

    return entries


def _score_entry(entry: Dict[str, Any], search_text: str) -> int:
    score = 0
    entry_text = entry.get("_text", "")

    for topic_name, keywords in TOPIC_KEYWORDS.items():
        for keyword in keywords:
            keyword_norm = _normalise_text(keyword)
            if not keyword_norm:
                continue
            if keyword_norm in entry_text:
                score += 4
            if keyword_norm in search_text:
                score += 2

    title_text = _normalise_text(entry.get("title", ""))
    topic_text = _normalise_text(entry.get("topic", ""))
    organisation_text = _normalise_text(entry.get("organisation", ""))

    for token in set(search_text.split()):
        if token and (token in title_text or token in topic_text or token in organisation_text or token in entry_text):
            score += 1

    return score


def _pick_relevant_content(entry: Dict[str, Any], search_text: str) -> List[str]:
    content = entry.get("content") or []
    if not isinstance(content, list):
        content = [str(content)]

    matched: List[str] = []
    for item in content:
        text = _normalise_text(item)
        if not text:
            continue
        if any(keyword in text for keyword in search_text.split() if keyword):
            matched.append(str(item))

    if matched:
        return matched[:3]

    return [str(item) for item in content[:2] if item is not None]


def retrieve_context(case_data: Dict[str, Any], top_k: int = 5) -> List[Dict[str, Any]]:
    """Return the most relevant official knowledge entries for a case."""
    if not isinstance(case_data, dict):
        return []

    search_text = _build_search_text(case_data)
    if not search_text.strip():
        return []

    ranked = []
    for entry in _load_knowledge_entries():
        score = _score_entry(entry, search_text)
        if score <= 0:
            continue
        relevant_content = _pick_relevant_content(entry, search_text)
        ranked.append({
            "title": entry.get("title"),
            "organisation": entry.get("organisation"),
            "topic": entry.get("topic"),
            "source_url": entry.get("source_url"),
            "relevant_content": relevant_content,
            "_score": score,
        })

    ranked.sort(key=lambda item: item["_score"], reverse=True)
    results = []
    for item in ranked[:max(0, int(top_k))]:
        results.append({
            "title": item["title"],
            "organisation": item["organisation"],
            "topic": item["topic"],
            "source_url": item["source_url"],
            "relevant_content": item["relevant_content"],
        })

    return results


def demo_retrieval():
    case = {
        "mainIssues": ["pay", "hours"],
        "pay": {
            "hourlyPay": 25,
            "payslipStatus": "no",
        },
        "employmentPattern": {
            "workPattern": "weekend",
            "overtimeStatus": "yes",
        },
    }

    results = retrieve_context(case, top_k=3)
    for item in results:
        print(json.dumps(item, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    demo_retrieval()
