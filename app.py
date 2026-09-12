"""VietRights Flask application entry point."""

from flask import Flask, current_app, jsonify, render_template, request

from services.config import ConfigurationError, Settings, sqlalchemy_database_url
from services.database import db
from services.llm import LLMBaseError, analyze_case
from services.retry import request_budget


def home():
    """Render the main landing and case intake page."""
    return render_template("index.html")


def analyze():
    """Analyze a workplace rights case and return guidance grounded in official sources."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({"status": "error", "error_code": "invalid_payload", "error": "Invalid JSON payload."}), 400
    try:
        with request_budget():
            result = analyze_case(data)
        return jsonify({"status": "success", **result})
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
