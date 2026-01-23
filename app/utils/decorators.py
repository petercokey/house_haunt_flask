from functools import wraps
from flask import jsonify, g, request
from app.utils.auth_helpers import jwt_required


# ==========================================================
# 🔹 Role-based Access Control (CORS-safe)
# ==========================================================
def role_required(role_name):
    """
    Requires a valid JWT and checks that the user has the given role.
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):

            # ✅ Allow preflight
            if request.method == "OPTIONS":
                return fn(*args, **kwargs)

            user = g.get("user")
            if not user:
                return jsonify({"error": "Unauthorized"}), 401

            if user.get("role") != role_name:
                return jsonify({
                    "error": f"Access denied. Requires '{role_name}' role."
                }), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ==========================================================
# 🔹 Admin-only decorator
# ==========================================================
def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):

        if request.method == "OPTIONS":
            return fn(*args, **kwargs)

        user = g.get("user")
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403

        return fn(*args, **kwargs)
    return wrapper
