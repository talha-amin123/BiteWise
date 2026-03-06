from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os

# Add project root to path so we can import matcher
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from matching.matcher import match_product

app = Flask(__name__)
CORS(app)  # Allow requests from Chrome extension


@app.route("/check", methods=["POST"])
def check_product():
    """
    Check if a product has any active recalls.

    Expects JSON: { "brand": "...", "product_name": "...", "size": "..." }
    Returns JSON: { "matches": [...] }
    """
    data = request.get_json()

    if not data:
        return jsonify({"error": "No JSON data provided"}), 400

    brand = data.get("brand", "")
    product_name = data.get("product_name", "")
    size = data.get("size", "")

    if not brand and not product_name:
        return jsonify({"error": "brand or product_name required"}), 400

    matches = match_product(brand, product_name, size)

    return jsonify({
        "query": {
            "brand": brand,
            "product_name": product_name,
            "size": size,
        },
        "match_count": len(matches),
        "matches": matches,
    })


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


if __name__ == "__main__":
    print("Starting BiteWise API on http://localhost:5000")
    app.run(debug=True, port=5000)