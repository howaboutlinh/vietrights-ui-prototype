from flask import Flask, jsonify, render_template, request

from services.llm import analyze_case

app = Flask(__name__)


@app.get("/")
def home():
    return render_template("index.html")


@app.post("/analyze")
def analyze():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return jsonify({
            "error": "Invalid JSON payload."
        }), 400

    try:
        result = analyze_case(data)
        return jsonify({"status": "success", **result})
    except RuntimeError as exc:
        return jsonify({
            "status": "error",
            "error": str(exc)
        }), 500
    except ValueError as exc:
        return jsonify({
            "status": "error",
            "error": f"Invalid model response: {exc}"
        }), 500
    except Exception as exc:
        return jsonify({
            "status": "error",
            "error": str(exc)
        }), 500


if __name__ == "__main__":
    app.run(debug=True, port=5001)