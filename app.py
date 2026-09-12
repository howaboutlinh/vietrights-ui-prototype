from flask import Flask, jsonify, render_template, request

from services.llm import LLMBaseError, analyze_case

app = Flask(__name__)


@app.get("/")
def home():
    """Render the main landing and case intake page."""
    return render_template("index.html")


@app.post("/analyze")
def analyze():
    """Analyze a workplace rights case and return guidance grounded in official sources."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "status": "error",
            "error_code": "invalid_payload",
            "error": "Invalid JSON payload."
        }), 400

    try:
        result = analyze_case(data)
        return jsonify({"status": "success", **result})
    except LLMBaseError as exc:
        app.logger.warning("Controlled LLM error: [%s] %s", exc.error_code, exc.safe_message)
        return jsonify({
            "status": "error",
            "error_code": exc.error_code,
            "error": exc.safe_message
        }), exc.status_code
    except ValueError as exc:
        app.logger.warning("Input validation error: %s", exc)
        return jsonify({
            "status": "error",
            "error_code": "invalid_input",
            "error": str(exc)
        }), 400
    except Exception as exc:
        app.logger.error("Unhandled server error: %s", exc, exc_info=True)
        return jsonify({
            "status": "error",
            "error_code": "internal_server_error",
            "error": "An unexpected server error occurred."
        }), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)