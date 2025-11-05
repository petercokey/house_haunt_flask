# app/utils/auth_helpers.py
from functools import wraps
from flask import request, jsonify, g
from flask_login import current_user, login_user
from app.models import User
import jwt
import os

SECRET_KEY = os.getenv("JWT_SECRET_KEY", "super-secret-jwt-key")

def jwt_or_login_required(role=None):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = None

            # 1️⃣ Check Flask-Login session
            if current_user.is_authenticated:
                user = current_user
            else:
                token = None

                # Try Authorization header first
                auth_header = request.headers.get("Authorization", "")
                if auth_header.startswith("Bearer "):
                    token = auth_header.split(" ")[1]
                # Or JWT cookie
                elif "access_token_cookie" in request.cookies:
                    token = request.cookies.get("access_token_cookie")

                if token:
                    try:
                        # Decode token created by Flask-JWT-Extended
                        data = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                        identity = data.get("sub")  # Flask-JWT-Extended stores identity here
                        if isinstance(identity, dict):
                            user_id = identity.get("id")
                        else:
                            user_id = identity
                        user = User.query.get(user_id)
                    except jwt.ExpiredSignatureError:
                        return jsonify({"error": "Token expired"}), 401
                    except jwt.InvalidTokenError:
                        return jsonify({"error": "Invalid token"}), 401

            if not user:
                return jsonify({"error": "Unauthorized. Please log in."}), 403

            # Role check (if specified)
            if role and user.role != role:
                return jsonify({"error": f"Access restricted to {role} users only."}), 403

            # Register the user in Flask-Login for this request context
            login_user(user)
            g.user = user

            return f(*args, **kwargs)
        return wrapper
    return decorator
