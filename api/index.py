import os
import random
from flask import Flask, jsonify, request
from flask_cors import CORS
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from dotenv import load_dotenv
import time
import jwt
from functools import wraps
from flask import send_from_directory

load_dotenv()

app = Flask(__name__)
PORTAL_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "portal"))
CORS(app, resources={r"/*": {"origins": "*"}}, allow_headers=["Content-Type", "Authorization"])

@app.before_request
def handle_preflight():
    # Let browsers complete CORS preflight without auth
    if request.method == "OPTIONS":
        return ("", 204)


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

# --- Admin Auth (JWT) ---
ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD")
JWT_SECRET = os.getenv("JWT_SECRET")

if not ADMIN_PASSWORD:
    raise RuntimeError("ADMIN_PASSWORD is not set")
if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set")

JWT_TTL_SECONDS = 60 * 60 * 12  # 12 hours


def _create_jwt(username: str) -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "role": "admin",
        "iat": now,
        "exp": now + JWT_TTL_SECONDS,
    }
    return jwt.encode(payload, JWT_SECRET, algorithm="HS256")


def _get_bearer_token() -> str | None:
    auth = request.headers.get("Authorization", "")
    if auth.startswith("Bearer "):
        return auth[len("Bearer "):].strip()
    return None


def require_admin(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if request.method == "OPTIONS":
            return ("", 204)
        token = _get_bearer_token()
        if not token:
            return {"error": "Missing Authorization: Bearer <token>"}, 401
        try:
            payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
            if payload.get("role") != "admin":
                return {"error": "Forbidden"}, 403
        except jwt.ExpiredSignatureError:
            return {"error": "Token expired"}, 401
        except jwt.InvalidTokenError:
            return {"error": "Invalid token"}, 401
        return f(*args, **kwargs)
    return wrapper

@app.get("/health")
def health():
    try:
        get_db().command("ping")
        return {"status": "ok", "db": "connected"}
    except ServerSelectionTimeoutError:
        return {"status": "error", "db": "unreachable"}, 500

@app.route("/auth/login", methods=["POST", "OPTIONS"])
def login():
    if request.method == "OPTIONS":
        return ("", 204)

    body = request.get_json(force=True) or {}
    username = body.get("username")
    password = body.get("password")

    if username != ADMIN_USERNAME or password != ADMIN_PASSWORD:
        return {"error": "Invalid credentials"}, 401

    token = _create_jwt(username)
    return {"token": token}, 200

@app.get("/ads")
def get_ads():
    ad_type = request.args.get("type")
    client_id = request.args.get("clientId")

    query = {}
    if ad_type:
        query["type"] = ad_type
    if client_id:
        query["clientId"] = client_id

    ads = list(ads_collection().find(query, {"_id": 0}))
    return jsonify(ads)

@app.post("/ads")
@require_admin
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
@require_admin
def update_ad(ad_id):
    updates = request.get_json(force=True)
    updates.pop("id", None)

    result = ads_collection().update_one({"id": ad_id}, {"$set": updates})
    if result.matched_count == 0:
        return {"error": "Ad not found"}, 404

    updated = ads_collection().find_one({"id": ad_id}, {"_id": 0})
    return jsonify(updated)

@app.delete("/ads/<ad_id>")
@require_admin
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
@require_admin
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
        return jsonify({"error": "clientId is required"}), 400

    # If no config exists yet, treat as "allow everything"
    config = configs_collection().find_one({"clientId": client_id}, {"_id": 0}) or {}
    allowed_types = config.get("allowedTypes", ["image", "video"])
    allowed_categories = config.get("allowedCategories", [])

    query = {
        "enabled": True,
        "clientId": client_id,
        "type": {"$in": allowed_types},
    }

    if requested_type:
        if requested_type not in allowed_types:
            return jsonify({"ad": None})
        query["type"] = requested_type

    if allowed_categories:
        query["categories"] = {"$in": allowed_categories}

    ads = list(ads_collection().find(query, {"_id": 0}))
    if not ads:
        return jsonify({"ad": None})

    return jsonify({"ad": random.choice(ads)})

@app.get("/portal/_debug")
def portal_debug():
    info = {
        "PORTAL_DIR": PORTAL_DIR,
        "exists": os.path.exists(PORTAL_DIR),
        "is_dir": os.path.isdir(PORTAL_DIR),
        "files": []
    }
    try:
        info["files"] = os.listdir(PORTAL_DIR)
    except Exception as e:
        info["error"] = str(e)
    return jsonify(info)


@app.get("/portal")
def portal_root():
    return send_from_directory(PORTAL_DIR, "login.html")

@app.get("/portal/<path:filename>")
def portal_files(filename):
    return send_from_directory(PORTAL_DIR, filename)
