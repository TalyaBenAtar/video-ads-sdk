from flask import Flask, jsonify, request
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/ads")
def get_ads():
    ad_type = request.args.get("type")

    ads = [
        {
            "id": "ad_1",
            "title": "Memory Game Power-Up!",
            "type": "image",
            "imageUrl": "https://example.com/ad1.png",
            "clickUrl": "https://example.com"
        },
        {
            "id": "ad_2",
            "title": "Watch to get an extra hint",
            "type": "video",
            "videoUrl": "https://example.com/ad2.mp4",
            "clickUrl": "https://example.com/hint"
        }
    ]

    if ad_type:
        ads = [a for a in ads if a.get("type") == ad_type]

    return jsonify(ads)

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
