import os
import random
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

_client = None

def get_db():
    global _client
    if _client is None:
        _client = MongoClient(
            os.getenv("MONGODB_URI"),
            serverSelectionTimeoutMS=3000
        )
    return _client["video_ads_db"]

def ads_collection():
    return get_db()["ads"]

def configs_collection():
    return get_db()["configs"]

mongo_uri = os.getenv("MONGODB_URI")
if not mongo_uri:
    raise RuntimeError("MONGODB_URI is not set")

@app.get("/health")
def health():
    try:
        get_db().command("ping")
        return {"status": "ok", "db": "connected"}
    except ServerSelectionTimeoutError:
        return {"status": "error", "db": "unreachable"}, 500

@app.get("/ads")
def get_ads():
    ad_type = request.args.get("type")
    query = {}
    if ad_type:
        query["type"] = ad_type

    ads = list(ads_collection().find(query, {"_id": 0}))
    return jsonify(ads)

@app.post("/ads")
def create_ad():
    ad = request.get_json(force=True)
    ad.setdefault("categories", [])
    ad.setdefault("enabled", True)

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

    ads_collection().update_one({"id": ad["id"]}, {"$set": ad}, upsert=True)
    return {"status": "created", "id": ad["id"]}, 201

@app.put("/ads/<ad_id>")
def update_ad(ad_id):
    updates = request.get_json(force=True)
    updates.pop("id", None)

    result = ads_collection().update_one({"id": ad_id}, {"$set": updates})
    if result.matched_count == 0:
        return {"error": "Ad not found"}, 404

    updated = ads_collection().find_one({"id": ad_id}, {"_id": 0})
    return jsonify(updated)

@app.delete("/ads/<ad_id>")
def delete_ad(ad_id):
    result = ads_collection().delete_one({"id": ad_id})
    if result.deleted_count == 0:
        return {"error": "Ad not found"}, 404

    return {"status": "deleted", "id": ad_id}

@app.get("/config/<client_id>")
def get_config(client_id):
    config = configs_collection().find_one(
        {"clientId": client_id},
        {"_id": 0}
    )

    if not config:
        return {"error": "Config not found"}, 404

    return jsonify(config)

@app.put("/config/<client_id>")
def upsert_config(client_id):
    data = request.get_json(force=True)

    config = {
        "clientId": client_id,
        "allowedTypes": data.get("allowedTypes", ["image", "video"]),
        "allowedCategories": data.get("allowedCategories", [])
    }

    configs_collection().update_one(
        {"clientId": client_id},
        {"$set": config},
        upsert=True
    )

    return jsonify(config)

@app.get("/ads/select")
def select_ad():
    client_id = request.args.get("clientId")
    requested_type = request.args.get("type")

    if not client_id:
        return {"error": "clientId is required"}, 400

    config = configs_collection().find_one(
        {"clientId": client_id},
        {"_id": 0}
    )

    if not config:
        return {"error": "Client config not found"}, 404

    allowed_types = config.get("allowedTypes", ["image", "video"])
    allowed_categories = config.get("allowedCategories", [])

    query = {
        "enabled": True,
        "type": {"$in": allowed_types}
    }

    if requested_type:
        if requested_type not in allowed_types:
            return {"ad": None}
        query["type"] = requested_type

    if allowed_categories:
        query["categories"] = {"$in": allowed_categories}

    ads = list(ads_collection().find(query, {"_id": 0}))
    if not ads:
        return {"ad": None}

    return jsonify(random.choice(ads))
