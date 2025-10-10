# app/utils/decorators.py
from functools import wraps
from flask import jsonify
from flask_login import current_user

def role_required(role):
    """Restrict access to a specific user role."""
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({"error": "Login required"}), 401

            if current_user.role != role:
                return jsonify({"error": f"Access restricted to {role}s only"}), 403

            return f(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(f):
    """Decorator for admin-only routes"""
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated:
            return jsonify({"error": "Login required"}), 401
        if current_user.role != "admin":
            return jsonify({"error": "Admins only"}), 403
        return f(*args, **kwargs)
    return wrapper
