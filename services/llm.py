import json
import os
from typing import Any, Dict, List

from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()


def _coerce_list(value: Any) -> List[str]:
    if value is None:
        return []
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str):
        return [value.strip()] if value.strip() else []
    return [str(value).strip()] if str(value).strip() else []


def _safe_parse_json(raw_response: str) -> Dict[str, Any]:
    try:
        return json.loads(raw_response)
    except json.JSONDecodeError:
        text = raw_response.strip()
        if not text:
            raise ValueError("OpenAI returned an empty response.")
        start = text.find("{")
        end = text.rfind("}")
        if start != -1 and end != -1 and end > start:
            return json.loads(text[start:end + 1])
        raise ValueError("OpenAI response was not valid JSON.")


def analyze_case(case_data: Dict[str, Any]) -> Dict[str, Any]:
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("Missing OPENAI_API_KEY environment variable.")

    client = OpenAI(api_key=api_key)
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

    try:
        response = client.responses.create(
            model="gpt-4o-mini",
            input=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            temperature=0.3,
        )
    except Exception as exc:
        raise RuntimeError(f"OpenAI API error: {exc}") from exc

    content = getattr(response, "output_text", None)
    if not content:
        output = getattr(response, "output", None) or []
        parts = []
        for item in output:
            if isinstance(item, dict):
                for value in item.get("content", []):
                    if isinstance(value, dict) and "text" in value:
                        parts.append(value["text"])
        content = "".join(parts)

    if not content:
        raise ValueError("OpenAI returned no usable content.")

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
