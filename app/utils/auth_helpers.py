# app/utils/auth_helpers.py
from functools import wraps
from flask import request, jsonify
from flask_login import current_user
from app.models import User
import jwt
import os
from datetime import datetime

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")

def jwt_or_login_required(role=None):
    """
    Hybrid decorator that supports both:
    - Flask-Login sessions (for browser cookies)
    - JWT tokens (for mobile / frontend fetch requests)
    Optionally restricts access by user role.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = None

            # 🧩 1. Try Flask-Login session first
            if current_user.is_authenticated:
                user = current_user

            # 🧩 2. If not logged in, try JWT from headers
            else:
                token = None
                if "Authorization" in request.headers:
                    auth_header = request.headers["Authorization"]
                    if auth_header.startswith("Bearer "):
                        token = auth_header.split(" ")[1]

                if token:
                    try:
                        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                        user = User.query.get(data.get("user_id"))
                    except jwt.ExpiredSignatureError:
                        return jsonify({"error": "Token expired"}), 401
                    except jwt.InvalidTokenError:
                        return jsonify({"error": "Invalid token"}), 401

            if not user:
                return jsonify({"error": "Unauthorized. Please log in."}), 403

            # 🧩 3. If role restriction is specified
            if role and user.role != role:
                return jsonify({"error": f"Access restricted to {role} users only."}), 403

            return f(*args, **kwargs)
        return wrapper
    return decorator
