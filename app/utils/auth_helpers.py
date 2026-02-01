import jwt
from functools import wraps
from flask import request, jsonify, g, current_app
from bson import ObjectId
from app.extensions import mongo


def jwt_required():
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"error": "Missing or invalid token"}), 401

            token = auth_header.split(" ")[1]

            try:
                payload = jwt.decode(
                    token,
                    current_app.config["SECRET_KEY"],
                    algorithms=["HS256"]
                )

                user = mongo.db.users.find_one(
                    {"_id": ObjectId(payload["user_id"])}
                )

                if not user:
                    return jsonify({"error": "User not found"}), 401

                g.user = user

            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except Exception:
                return jsonify({"error": "Invalid token"}), 401

            return fn(*args, **kwargs)

        return wrapper
    return decorator

def role_required(role_name):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            user = g.get("user")
            if not user:
                return jsonify({"error": "Unauthorized"}), 401

            if user.get("role") != role_name:
                return jsonify({"error": f"Access denied. Requires '{role_name}' role."}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator

    from functools import wraps
from flask import jsonify, g


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
