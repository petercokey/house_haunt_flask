from functools import wraps
from flask import jsonify, g
from app.utils.auth_helpers import jwt_required


# ==========================================================
# 🔹 Role-based Access Control Decorator
# ==========================================================
def role_required(role_name):
    """
    Requires a valid JWT and checks that the user has the given role.
    Usage:
        @role_required("agent")
        def protected_route(): ...
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user = g.get("user")
            if not user:
                return jsonify({"error": "Unauthorized"}), 401

            if user.get("role") != role_name:
                return jsonify({"error": f"Access denied. Requires '{role_name}' role."}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ==========================================================
# 🔹 Admin check decorator
# ==========================================================
def admin_required(fn):
    """
    Ensures that the logged-in user is an admin.
    """
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = g.get("user")
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper
