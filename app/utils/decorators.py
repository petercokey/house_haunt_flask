from functools import wraps
from flask import jsonify, g
from app.utils.auth_helpers import jwt_required

# 🔹 Role-based access
# ==========================================================
def role_required(role_name):
    """
    Restrict access to users with a specific role.
    Usage:
        @role_required("agent")
        def my_route(): ...
    """
    def decorator(fn):
        @wraps(fn)
        @jwt_required()
        def wrapper(*args, **kwargs):
            user = g.get("user")
            if not user:
                return jsonify({"error": "Unauthorized"}), 401

            if user.get("role") != role_name:
                return jsonify({"error": f"Access restricted to '{role_name}' only"}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ==========================================================
# 🔹 Admin-only access
# ==========================================================
def admin_required(fn):
    """
    Restrict access to admin users only.
    Usage:
        @admin_required
        def admin_route(): ...
    """
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = g.get("user")
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper
