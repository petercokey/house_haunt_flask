# app/utils/auth_helpers.py
from functools import wraps
from flask import jsonify
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from flask_login import current_user, login_required
from app.models import User
import jwt
import os
from datetime import datetime

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")

def jwt_or_login_required(role=None):
    """
    Allows access if the user is authenticated via JWT or Flask-Login.
    Optionally enforces a specific role (e.g. "agent" or "admin").
    """
    def wrapper(fn):
        @wraps(fn)
        def decorator(*args, **kwargs):
            user = None

            # Try JWT-based auth first
            try:
                verify_jwt_in_request(optional=True)
                identity = get_jwt_identity()
                if identity:
                    user = User.query.filter_by(id=identity).first()
            except Exception:
                pass

            # Fallback: Flask-Login session
            if not user and not current_user.is_authenticated:
                return jsonify({"error": "Authentication required"}), 401

            user = user or current_user

            # Role check
            if role and getattr(user, "role", None) != role:
                return jsonify({"error": f"{role.capitalize()} access only"}), 403

            return fn(*args, **kwargs)
        return decorator
    return wrapper
