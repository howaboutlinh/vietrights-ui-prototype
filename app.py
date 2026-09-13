"""VietRights Flask application entry point."""

from flask import Flask, current_app, jsonify, render_template, request
import os

from services.config import ConfigurationError, Settings, sqlalchemy_database_url
from services.database import db
from services.llm import LLMAuthenticationError, LLMBaseError, LLMInvalidResponseError, LLMQuotaError, LLMServiceError, LLMTimeoutError, analyze_case
from services.retry import request_budget


def home():
    """Render the main landing and case intake page."""
    return render_template("index.html")


def diagnostic_error_response(status_code, stage):
    return jsonify({
        "success": False,
        "error": "AI_ANALYSIS_FAILED",
        "stage": stage,
        "message": "The AI analysis service is currently unavailable.",
    }), status_code


def analyze():
    """Analyze a workplace rights case and return guidance grounded in official sources."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "error_code": "invalid_payload", "error": "Invalid JSON payload."}), 400
    try:
        current_app.logger.info(
            "Starting Gemini analysis model=%s api_key_configured=%s",
            os.getenv("GEMINI_CHAT_MODEL", os.getenv("GEMINI_MODEL", "gemini-3.6-flash")),
            bool(os.getenv("GEMINI_API_KEY") or os.getenv("GOOGLE_API_KEY")),
        )
        with request_budget():
            result = analyze_case(data)
        if result.get("ai_used") is True:
            current_app.logger.info("Gemini analysis succeeded")
        return jsonify({"status": "success", **result})
    except LLMAuthenticationError as exc:
        current_app.logger.exception("Gemini analysis failed at stage: %s", exc.stage)
        return diagnostic_error_response(503, "client_setup")
    except (LLMQuotaError, LLMTimeoutError, LLMServiceError) as exc:
        current_app.logger.exception("Gemini analysis failed at stage: %s", exc.stage)
        return diagnostic_error_response(503, "gemini_request")
    except LLMInvalidResponseError as exc:
        current_app.logger.exception("Gemini analysis failed at stage: %s", exc.stage)
        stage = exc.stage if exc.stage in {"response_parsing", "schema_validation"} else "unknown"
        return diagnostic_error_response(500, stage)
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
        current_app.logger.exception("Gemini analysis failed at stage: unknown")
        return jsonify({
            "success": False,
            "error": "AI_ANALYSIS_FAILED",
            "stage": "unknown",
            "message": "The AI analysis service is currently unavailable.",
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
    flask_app.add_url_rule("/api/analyze", "api_analyze", analyze, methods=["POST"])
    return flask_app


app = create_app()


if __name__ == "__main__":
    app.run(debug=True, port=5001)
