from functools import wraps
from flask import jsonify, g, request
from app.utils.auth_helpers import jwt_required

def role_required(role_name):
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):

            # ✅ ALLOW PREFLIGHT
            if request.method == "OPTIONS":
                return "", 200

            user = g.get("user")
            if not user:
                return jsonify({"error": "Unauthorized"}), 401

            if user.get("role") != role_name:
                return jsonify({"error": "Forbidden"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


