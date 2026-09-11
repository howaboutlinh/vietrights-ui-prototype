import json
import os
import time
from typing import Any, Dict, List

from dotenv import load_dotenv
from google import genai
from google.genai import types

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


def analyze_case(case_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing GEMINI_API_KEY environment variable.")

    client = genai.Client(api_key=api_key)
    system_prompt = (
        "Bạn là người hỗ trợ hướng dẫn về quyền lao động cho người Việt làm việc ở Úc. "
        "Hãy trả lời bằng tiếng Việt, rõ ràng, dễ hiểu, không dùng thuật ngữ pháp lý quá chuyên. "
        "Tập trung vào người lao động di cư Việt Nam ở Úc. "
        "Không đưa ra kết luận pháp lý chắc chắn. Luôn nêu rõ sự không chắc chắn khi thiếu thông tin. "
        "Nếu thông tin quan trọng còn thiếu, hãy đặt tối đa 1-2 câu hỏi làm rõ. "
        "Nếu người dùng không biết câu trả lời, vẫn cung cấp hướng dẫn chung có ích. "
        "Không bịa nguồn chính thức, không nói về mức lương tối thiểu hoặc award cụ thể nếu chưa có thông tin chính thức. "
        "Bạn chỉ trả về JSON hợp lệ theo định dạng đã yêu cầu."
    )

    user_prompt = (
        "Dựa trên dữ liệu tình huống dưới đây, hãy tạo phản hồi ngắn gọn nhưng có giá trị cho người lao động Việt Nam ở Úc. "
        "Nội dung phải rõ ràng, mang tính hướng dẫn tổng quát, không phải tư vấn pháp lý chắc chắn. "
        "Trả về JSON với các trường: summary, issues, evidence, next_steps, clarification_questions, risk_level. "
        "risk_level phải là một trong: low, medium, high. "
        "Nếu thiếu thông tin quan trọng, đưa tối đa 1-2 câu hỏi làm rõ trong clarification_questions. "
        "Các mảng phải là danh sách chuỗi. "
        "Không thêm các trường khác. "
        "Dữ liệu tình huống:\n"
        + json.dumps(case_data, ensure_ascii=False)
    )

    model_name = "gemini-3.6-flash"
    max_retries = 2
    last_exc = None

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
            last_exc = exc
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

    required = ["summary", "issues", "evidence", "next_steps", "clarification_questions", "risk_level"]
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
    }

    if result["risk_level"] not in {"low", "medium", "high"}:
        result["risk_level"] = "medium"

    return result
