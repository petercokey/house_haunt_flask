from functools import wraps
from flask import request, jsonify, g
import jwt
from bson import ObjectId
from app.extensions import mongo
from flask import current_app


# ===============================
# JWT REQUIRED
# ===============================
def jwt_required():
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth = request.headers.get("Authorization")

            if not auth or not auth.startswith("Bearer "):
                return jsonify({"error": "Missing or invalid token"}), 401

            token = auth.split(" ")[1]

            try:
                payload = jwt.decode(
                    token,
                    current_app.config["SECRET_KEY"],
                    algorithms=["HS256"]
                )
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 401

            user = mongo.db.users.find_one(
                {"_id": ObjectId(payload["user_id"])}
            )

            if not user:
                return jsonify({"error": "User not found"}), 401

            g.user = user
            return fn(*args, **kwargs)

        return wrapper
    return decorator


# ===============================
# ROLE REQUIRED
# ===============================
def role_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = getattr(g, "user", None)

            if not user:
                return jsonify({"error": "Authentication required"}), 401

            if user.get("role") != role:
                return jsonify({"error": f"Role '{role}' required"}), 403

            return fn(*args, **kwargs)

        return wrapper
    return decorator


# ===============================
# ADMIN REQUIRED
# ===============================
def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = getattr(g, "user", None)

        if not user:
            return jsonify({"error": "Authentication required"}), 401

        if user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403

        return fn(*args, **kwargs)

    return wrapper

