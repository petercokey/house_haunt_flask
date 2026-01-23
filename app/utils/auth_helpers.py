from functools import wraps
from flask import request, jsonify, g
import jwt, os
from app import mongo
from bson import ObjectId

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")


# ==========================================================
# 🔹 Core JWT Authentication Decorator (CORS-safe)
# ==========================================================
def jwt_required():
    """
    Ensures the request includes a valid JWT token.
    Skips authentication for OPTIONS (CORS preflight).
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):

            # ✅ Allow CORS preflight through unchallenged
            if request.method == "OPTIONS":
                return fn(*args, **kwargs)

            token = (
                request.cookies.get("access_token_cookie")
                or request.headers.get("Authorization", "").replace("Bearer ", "")
            )

            if not token:
                return jsonify({"error": "Missing authentication token"}), 401

            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get("user_id")

                if not user_id:
                    return jsonify({"error": "Invalid token payload"}), 401

                user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
                if not user:
                    return jsonify({"error": "User not found"}), 404

                g.user = user

            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 401

            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ==========================================================
# 🔹 Utility: get_authenticated_user()
# ==========================================================
def get_authenticated_user():
    token = (
        request.cookies.get("access_token_cookie")
        or request.headers.get("Authorization", "").replace("Bearer ", "")
    )

    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return mongo.db.users.find_one(
            {"_id": ObjectId(payload.get("user_id"))}
        )
    except Exception:
        return None
