"""VietRights Flask application entry point."""

from flask import Flask, current_app, jsonify, render_template, request

from services.config import ConfigurationError, Settings, sqlalchemy_database_url
from services.database import db
from services.llm import LLMBaseError, LLMQuotaError, LLMServiceError, LLMTimeoutError, analyze_case
from services.retry import request_budget


def home():
    """Render the main landing and case intake page."""
    return render_template("index.html")


TRUSTED_FALLBACK_SOURCES = [
    {"number": 1, "title": "Fair Work Ombudsman", "organisation": "Fair Work Ombudsman", "url": "https://www.fairwork.gov.au/"},
    {"number": 2, "title": "Department of Home Affairs", "organisation": "Department of Home Affairs", "url": "https://www.homeaffairs.gov.au/"},
    {"number": 3, "title": "SafeWork NSW", "organisation": "SafeWork NSW", "url": "https://www.safework.nsw.gov.au/"},
    {"number": 4, "title": "RMWC Migrant Workers Hub", "organisation": "RMWC", "url": "https://unionsnsw.org.au/your-rights/migrant-workers/"},
]


def fallback_response(case_data):
    """Return safe bilingual guidance when Gemini is temporarily unavailable."""
    language = "en" if str(case_data.get("language") or "vi").lower() == "en" else "vi"
    issues = {str(issue).strip() for issue in case_data.get("mainIssues") or []}
    if language == "vi":
        rules = {
            "pay": "Ghi lại giờ làm, các khoản thanh toán và kiểm tra mức lương tối thiểu phù hợp với Fair Work Ombudsman.",
            "payslip": "Giữ hồ sơ ngân hàng và tin nhắn liên quan, đồng thời liên hệ Fair Work Ombudsman.",
            "hours": "Ghi lại roster, ca làm, giờ làm thêm và thời gian nghỉ.",
            "visa": "Người lao động di trú vẫn có quyền tại nơi làm việc. Xem thông tin từ Home Affairs.",
            "safety": "Nếu có nguy hiểm ngay lập tức, gọi 000; nếu không khẩn cấp, liên hệ SafeWork NSW.",
            "harassment": "Giữ lại tin nhắn và tìm hỗ trợ phù hợp.",
            "other": "Ghi lại sự việc, giữ tài liệu liên quan và tìm hỗ trợ phù hợp.",
        }
        summary = "Gemini đang tạm thời không khả dụng. Dưới đây là hướng dẫn dự phòng từ các nguồn chính thức."
    else:
        rules = {
            "pay": "Record hours and payments, and check the applicable minimum rate with the Fair Work Ombudsman.",
            "payslip": "Preserve bank records and messages, and contact the Fair Work Ombudsman.",
            "hours": "Record rosters, shifts, overtime and breaks.",
            "visa": "Migrant workers still have workplace rights. Review information from Home Affairs.",
            "safety": "If there is immediate danger call 000; otherwise contact SafeWork NSW.",
            "harassment": "Preserve messages and seek appropriate support.",
            "other": "Record what happened, preserve relevant documents and seek appropriate support.",
        }
        summary = "Gemini is temporarily unavailable. The following is fallback guidance from official sources."
    issue_guidance = [rules[issue] for issue in issues if issue in rules]
    return {
        "status": "success",
        "fallback": True,
        "summary": summary,
        "answer": summary,
        "issues": issue_guidance,
        "evidence": [],
        "next_steps": [],
        "clarification_questions": [],
        "risk_level": "medium",
        "sources": TRUSTED_FALLBACK_SOURCES,
        "content_format": "markdown",
        "retrieval": {"used": True, "result_count": 0},
    }


def analyze():
    """Analyze a workplace rights case and return guidance grounded in official sources."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "error_code": "invalid_payload", "error": "Invalid JSON payload."}), 400
    try:
        with request_budget():
            result = analyze_case(data)
        return jsonify({"status": "success", **result})
    except (LLMQuotaError, LLMTimeoutError, LLMServiceError):
        current_app.logger.warning("Gemini temporarily unavailable; returning fallback guidance")
        return jsonify(fallback_response(data)), 200
    except LLMBaseError as exc:
        current_app.logger.warning("Controlled LLM error code=%s", exc.error_code)
        return jsonify({"status": "error", "error_code": exc.error_code, "error": exc.safe_message}), exc.status_code
    except ConfigurationError:
        current_app.logger.warning("RAG service is not configured")
        return jsonify({
            "status": "error",
            "error_code": "service_unconfigured",
            "error": "The knowledge service is not configured yet. Please contact the administrator.",
        }), 503
    except ValueError as exc:
        current_app.logger.warning("Input validation failed")
        return jsonify({"status": "error", "error_code": "invalid_input", "error": str(exc)}), 400
    except Exception:
        current_app.logger.error("Unhandled server error")
        return jsonify({
            "status": "error",
            "error_code": "internal_server_error",
            "error": "An unexpected server error occurred.",
        }), 500


def create_app() -> Flask:
    """Create the app; initialize SQLAlchemy only when DATABASE_URL is configured."""
    flask_app = Flask(__name__)
    settings = Settings.from_env()
    if settings.database_url:
        flask_app.config.update(
            SQLALCHEMY_DATABASE_URI=sqlalchemy_database_url(settings.database_url),
            SQLALCHEMY_TRACK_MODIFICATIONS=False,
            SQLALCHEMY_ENGINE_OPTIONS={
                "pool_pre_ping": True,
                "pool_recycle": 300,
                "pool_size": 3,
                "max_overflow": 2,
                "pool_timeout": 30,
                "connect_args": {"sslmode": "require"},
            },
        )
        db.init_app(flask_app)
    flask_app.add_url_rule("/", "home", home, methods=["GET"])
    flask_app.add_url_rule("/analyze", "analyze", analyze, methods=["POST"])
    return flask_app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
