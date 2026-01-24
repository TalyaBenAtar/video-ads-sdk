import os
import random
import hashlib, hmac, secrets
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

def users_collection():
    return get_db()["users"]

def _hash_password(password: str, salt: str | None = None) -> str:
    """
    Stores: pbkdf2$<salt>$<hash>
    """
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        200_000,
    )
    return f"pbkdf2${salt}${dk.hex()}"

def _verify_password(password: str, stored: str) -> bool:
    try:
        scheme, salt, hexhash = stored.split("$", 2)
        if scheme != "pbkdf2":
            return False
        candidate = _hash_password(password, salt=salt)
        return hmac.compare_digest(candidate, stored)
    except Exception:
        return False


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


def _create_jwt(username: str, role: str, allowed_client_ids: list[str] | None = None) -> str:
    now = int(time.time())
    payload = {
        "sub": username,
        "role": role,
        "allowedClientIds": allowed_client_ids or [],
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

def get_auth():
    """
    Returns dict: {"username": str, "role": str, "allowedClientIds": list[str]}
    """
    auth = request.headers.get("Authorization", "")
    if not auth.startswith("Bearer "):
        return None
    token = auth.split(" ", 1)[1].strip()
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
        return {
            "username": payload.get("sub"),
            "role": payload.get("role"),
            "allowedClientIds": payload.get("allowedClientIds") or [],
        }
    except Exception:
        return None

def require_auth(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = get_auth()
        if not user:
            return {"error": "Unauthorized"}, 401
        request.user = user  # attach
        return fn(*args, **kwargs)
    return wrapper

def require_client_access(client_id: str) -> bool:
    user = getattr(request, "user", None) or get_auth()
    if not user:
        return False
    if user["role"] == "admin":
        return True
    return client_id in (user.get("allowedClientIds") or [])


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
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""

    # 1) Admin login (existing behavior)
    if username == ADMIN_USERNAME and password == ADMIN_PASSWORD:
        token = _create_jwt(username=username, role="admin")
        return {"token": token}, 200

    # 2) Developer login (DB-backed)
    user = users_collection().find_one({"username": username}, {"_id": 0})
    if not user:
        return {"error": "Invalid credentials"}, 401

    if not _verify_password(password, user.get("passwordHash", "")):
        return {"error": "Invalid credentials"}, 401

    role = user.get("role", "developer")
    allowed = user.get("allowedClientIds", [])

    token = _create_jwt(username=username, role=role, allowed_client_ids=allowed)
    return {"token": token}, 200

@app.route("/auth/register", methods=["POST", "OPTIONS"])
def register():
    if request.method == "OPTIONS":
        return ("", 204)

    body = request.get_json(force=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    client_id = (body.get("clientId") or "").strip()

    if not username or not password or not client_id:
        return {"error": "username, password, and clientId are required"}, 400

    # Basic clientId hygiene
    if len(client_id) < 3 or " " in client_id:
        return {"error": "clientId must be at least 3 chars and contain no spaces"}, 400

    # Prevent stealing an existing app/clientId
    existing_cfg = configs_collection().find_one({"clientId": client_id}, {"_id": 1})
    existing_ads = ads_collection().find_one({"clientId": client_id}, {"_id": 1})
    if existing_cfg or existing_ads:
        return {"error": "clientId already exists. Choose a different one."}, 409

    # Prevent duplicate usernames
    existing_user = users_collection().find_one({"username": username}, {"_id": 1})
    if existing_user:
        return {"error": "username already exists"}, 409

    # Create developer user tied to this clientId
    doc = {
        "username": username,
        "passwordHash": _hash_password(password),
        "role": "developer",
        "allowedClientIds": [client_id],
    }
    users_collection().insert_one(doc)

    # Create default config so /ads/select works immediately
    configs_collection().update_one(
        {"clientId": client_id},
        {"$set": {"clientId": client_id, "allowedTypes": ["image", "video"], "allowedCategories": []}},
        upsert=True
    )

    # Auto-login: return token
    token = _create_jwt(username=username, role="developer", allowed_client_ids=[client_id])
    return {"token": token}, 201


@app.post("/admin/users")
@require_admin
def admin_create_user():
    body = request.get_json(force=True) or {}
    username = (body.get("username") or "").strip()
    password = body.get("password") or ""
    role = body.get("role") or "developer"
    allowed = body.get("allowedClientIds") or []

    if not username or not password:
        return {"error": "username and password are required"}, 400
    if role not in ["admin", "developer"]:
        return {"error": "role must be admin or developer"}, 400
    if not isinstance(allowed, list):
        return {"error": "allowedClientIds must be a list"}, 400

    doc = {
        "username": username,
        "passwordHash": _hash_password(password),
        "role": role,
        "allowedClientIds": allowed,
    }

    users_collection().update_one({"username": username}, {"$set": doc}, upsert=True)
    return {"status": "created", "username": username, "role": role, "allowedClientIds": allowed}, 201


@app.get("/ads")
@require_auth
def list_ads():
    client_id = request.args.get("clientId")

    user = request.user
    if user["role"] == "admin":
        query = {}
        if client_id:
            query["clientId"] = client_id
    else:
        allowed = user["allowedClientIds"]
        if client_id:
            if client_id not in allowed:
                return {"error": "Forbidden"}, 403
            query = {"clientId": client_id}
        else:
            query = {"clientId": {"$in": allowed}}

    ads = list(ads_collection().find(query, {"_id": 0}))
    return ads, 200

@app.post("/ads")
@require_auth
def create_ad():
    body = request.get_json(force=True) or {}

    client_id = (body.get("clientId") or "").strip()
    if not client_id:
        return {"error": "clientId is required"}, 400

    if not require_client_access(client_id):
        return {"error": "Forbidden"}, 403

    required = ["id", "title", "type", "clickUrl"]
    missing = [k for k in required if not body.get(k)]
    if missing:
        return {"error": f"Missing fields: {', '.join(missing)}"}, 400

    if body["type"] not in ["image", "video"]:
        return {"error": "type must be 'image' or 'video'"}, 400

    if body["type"] == "image" and not body.get("imageUrl"):
        return {"error": "imageUrl is required for image ads"}, 400

    if body["type"] == "video" and not body.get("videoUrl"):
        return {"error": "videoUrl is required for video ads"}, 400

    ads_collection().update_one({"id": body["id"]}, {"$set": body}, upsert=True)
    return {"status": "created", "id": body["id"]}, 201

def _get_ad_or_404(ad_id: str):
    ad = ads_collection().find_one({"id": ad_id}, {"_id": 0})
    if not ad:
        return None
    return ad

@app.put("/ads/<ad_id>")
@require_auth
def update_ad(ad_id):
    existing = _get_ad_or_404(ad_id)
    if not existing:
        return {"error": "Not found"}, 404

    if not require_client_access(existing["clientId"]):
        return {"error": "Forbidden"}, 403

    body = request.get_json(force=True) or {}

    #  prevent dev from changing clientId ownership
    if request.user["role"] != "admin":
        body.pop("clientId", None)
        body.pop("id", None)

    ads_collection().update_one({"id": ad_id}, {"$set": body})
    updated = ads_collection().find_one({"id": ad_id}, {"_id": 0})
    return updated, 200


@app.delete("/ads/<ad_id>")
@require_auth
def delete_ad(ad_id):
    existing = _get_ad_or_404(ad_id)
    if not existing:
        return {"error": "Not found"}, 404

    if not require_client_access(existing["clientId"]):
        return {"error": "Forbidden"}, 403

    ads_collection().delete_one({"id": ad_id})
    return {"status": "deleted", "id": ad_id}, 200

@app.get("/config/<client_id>")
@require_auth
def get_config(client_id):
    if not require_client_access(client_id):
        return {"error": "Forbidden"}, 403

    cfg = configs_collection().find_one({"clientId": client_id}, {"_id": 0})
    if not cfg:
        cfg = {"clientId": client_id, "allowedTypes": ["image","video"], "allowedCategories": []}
    return cfg, 200


@app.put("/config/<client_id>")
@require_auth
def put_config(client_id):
    if not require_client_access(client_id):
        return {"error": "Forbidden"}, 403

    body = request.get_json(force=True) or {}
    allowed_types = body.get("allowedTypes") or ["image","video"]
    allowed_categories = body.get("allowedCategories") or []

    doc = {
        "clientId": client_id,
        "allowedTypes": allowed_types,
        "allowedCategories": allowed_categories,
    }
    configs_collection().update_one({"clientId": client_id}, {"$set": doc}, upsert=True)
    return doc, 200

 
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


@app.get("/me")
@require_auth
def me():
    return request.user, 200

@app.post("/apps")
@require_auth
def add_app():
    """
    Developer can add a clientId to their own allowed list.
    Admin can add too (optional, but harmless).
    """
    body = request.get_json(force=True) or {}
    client_id = (body.get("clientId") or "").strip()

    if not client_id:
        return {"error": "clientId is required"}, 400

    # basic sanity (optional)
    if len(client_id) < 2 or len(client_id) > 64:
        return {"error": "clientId length must be 2..64"}, 400

    username = request.user["username"]
    role = request.user["role"]

    if role == "admin":
        # admin doesn't really need it, but allow anyway
        return {"status": "ok", "clientId": client_id}, 200

    # Upsert user and add to allowed list
    users_collection().update_one(
        {"username": username},
        {"$addToSet": {"allowedClientIds": client_id}},
        upsert=True
    )

    # Return updated list (nice for UI)
    user = users_collection().find_one({"username": username}, {"_id": 0, "allowedClientIds": 1})
    return {"status": "added", "clientId": client_id, "allowedClientIds": (user or {}).get("allowedClientIds", [])}, 200


@app.get("/portal")
def portal_root():
    return send_from_directory(PORTAL_DIR, "login.html")

@app.get("/portal/<path:filename>")
def portal_files(filename):
    return send_from_directory(PORTAL_DIR, filename)
