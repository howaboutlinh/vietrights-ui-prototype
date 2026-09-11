import json
import os
import time
from typing import Any, Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import types

from services.retrieval import retrieve_context

load_dotenv()


def _is_retryable_gemini_error(exc: Exception) -> bool:
    status_code = getattr(exc, "status_code", None)
    if status_code is not None:
        status_code = str(status_code).upper()
        if status_code in {"503", "UNAVAILABLE"}:
            return True

    text = str(exc).upper()
    return "503" in text or "UNAVAILABLE" in text


def _coerce_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value).strip()] if str(value).strip() else []


def _safe_parse_json(raw_response: str) -> Dict[str, Any]:
    text = str(raw_response or '').strip()
    if not text:
        raise ValueError("Gemini returned an empty response.")

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
            return json.loads(text[start:end + 1])
        raise ValueError("Gemini response was not valid JSON.")


def _format_context_for_prompt(context_entries: List[Dict[str, Any]]) -> str:
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


def analyze_case(case_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable.")

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

    client = genai.Client(api_key=api_key)
    system_prompt = (
        "Bạn là người hỗ trợ hướng dẫn về quyền lao động cho người Việt làm việc ở Úc. "
        "Hãy trả lời bằng tiếng Việt, rõ ràng, dễ hiểu, không dùng thuật ngữ pháp lý quá chuyên. "
        "Tập trung vào người lao động di cư Việt Nam ở Úc. "
        "Sử dụng bối cảnh chính thức được cung cấp làm căn cứ chính cho thông tin về quyền lao động. "
        "Không bịa luật, mức lương, hay sự kiện pháp lý không được hỗ trợ bởi bối cảnh đã cho. "
        "Nếu bối cảnh không đủ, hãy nêu rõ điều nào chưa xác nhận được. "
        "Không đưa ra kết luận pháp lý chắc chắn. "
        "Nếu thông tin quan trọng còn thiếu, hãy đặt tối đa 1-2 câu hỏi làm rõ. "
        "Nếu người dùng không biết câu trả lời, vẫn cung cấp hướng dẫn chung an toàn. "
        "Bạn chỉ trả về JSON hợp lệ theo định dạng đã yêu cầu."
    )

    user_prompt = (
        "Dựa trên dữ liệu tình huống và bối cảnh chính thức dưới đây, hãy tạo phản hồi ngắn gọn nhưng có giá trị cho người lao động Việt Nam ở Úc. "
        "Mọi thông tin về quyền lao động phải dựa trên bối cảnh chính thức được cung cấp. "
        "Nếu không có nguồn chính thức phù hợp, hãy nói rõ rằng câu trả lời không được căn cứ trên nguồn chính thức phù hợp. "
        "Trả về JSON với các trường: summary, issues, evidence, next_steps, clarification_questions, risk_level, sources. "
        "risk_level phải là một trong: low, medium, high. "
        "sources phải là mảng các object có đúng 3 trường: title, organisation, url. Chỉ lấy từ bối cảnh chính thức đã cung cấp. "
        "Nếu không có nguồn phù hợp, sources phải là mảng rỗng. "
        "Không thêm các trường khác. "
        "Dữ liệu tình huống:\n"
        + json.dumps(case_data, ensure_ascii=False)
        + "\n\nBối cảnh chính thức:\n"
        + formatted_context
    )

    model_name = "gemini-3.6-flash"
    max_retries = 2

    for attempt in range(max_retries + 1):
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=user_prompt,
                config=types.GenerateContentConfig(
                    system_instruction=system_prompt,
                    temperature=0.3,
                    response_mime_type="application/json",
                ),
            )
            break
        except Exception as exc:
            if attempt >= max_retries or not _is_retryable_gemini_error(exc):
                raise RuntimeError(f"Gemini API error: {exc}") from exc
            time.sleep(1.5)

    content = getattr(response, "text", None)
    if not content:
        try:
            content = response.candidates[0].content.parts[0].text
        except Exception:
            content = ""

    if not content:
        raise ValueError("Gemini returned no usable content.")

    parsed = _safe_parse_json(content)

    required = ["summary", "issues", "evidence", "next_steps", "clarification_questions", "risk_level", "sources"]
    for key in required:
        if key not in parsed:
            raise ValueError(f"Missing required field: {key}")

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

    if not source_refs:
        result["sources"] = []
    else:
        result["sources"] = [
            {
                "title": item["title"],
                "organisation": item["organisation"],
                "url": item["url"],
            }
            for item in source_refs
            if item.get("title") or item.get("organisation") or item.get("url")
        ]

    return result
