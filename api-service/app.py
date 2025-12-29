import os
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

mongo_uri = os.getenv("MONGODB_URI")
if not mongo_uri:
    raise RuntimeError("MONGODB_URI is not set. Create api-service/.env and put it there.")

client = MongoClient(mongo_uri)
db = client["video_ads_db"]
ads_collection = db["ads"]


@app.get("/health")
def health():
    client.admin.command("ping")
    return {"status": "ok", "db": "connected"}


@app.get("/ads")
def get_ads():
    ad_type = request.args.get("type")
    query = {}
    if ad_type:
        query["type"] = ad_type

    ads = list(ads_collection.find(query, {"_id": 0}))
    return jsonify(ads)

@app.post("/ads")
def create_ad():
    ad = request.get_json(force=True)

    required = ["id", "title", "type", "clickUrl"]
    missing = [k for k in required if k not in ad]
    if missing:
        return {"error": f"Missing fields: {', '.join(missing)}"}, 400

    if ad["type"] not in ["image", "video"]:
        return {"error": "type must be 'image' or 'video'"}, 400

    if ad["type"] == "image" and "imageUrl" not in ad:
        return {"error": "imageUrl is required for image ads"}, 400

    if ad["type"] == "video" and "videoUrl" not in ad:
        return {"error": "videoUrl is required for video ads"}, 400

    # upsert by id so repeated tests don't create duplicates
    ads_collection.update_one({"id": ad["id"]}, {"$set": ad}, upsert=True)
    return {"status": "created", "id": ad["id"]}, 201

@app.put("/ads/<ad_id>")
def update_ad(ad_id: str):
    updates = request.get_json(force=True)

    # don't allow changing id via update
    updates.pop("id", None)

    result = ads_collection.update_one({"id": ad_id}, {"$set": updates})
    if result.matched_count == 0:
        return {"error": "Ad not found"}, 404

    updated = ads_collection.find_one({"id": ad_id}, {"_id": 0})
    return jsonify(updated), 200


@app.delete("/ads/<ad_id>")
def delete_ad(ad_id: str):
    result = ads_collection.delete_one({"id": ad_id})
    if result.deleted_count == 0:
        return {"error": "Ad not found"}, 404

    return {"status": "deleted", "id": ad_id}, 200



if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True, use_reloader=False)

