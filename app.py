from flask import Flask, render_template, request, jsonify

app = Flask(__name__)

@app.get("/")
def home():
    return render_template("index.html")

@app.post("/analyze")
def analyze():
    data = request.get_json()

    print("Received case:")
    print(data)

    return jsonify({
        "status": "success",
        "summary": "Your case was received.",
        "issues": [
            "Possible workplace issue"
        ],
        "next_steps": [
            "Check the applicable workplace rules"
        ]
    })

if __name__ == "__main__":
    app.run(debug=True, port=5001)