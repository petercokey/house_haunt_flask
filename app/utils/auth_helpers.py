# app/utils/auth_helpers.py
from functools import wraps
from flask import request, jsonify
from flask_login import current_user, login_required
import jwt
from datetime import datetime, timedelta
from app.models import User
from app import db
import os


def generate_jwt(user):
    """Generate a JWT token for the given user."""
    secret = os.getenv("SECRET_KEY", "super-secret-key")
    payload = {
        "user_id": user.id,
        "exp": datetime.utcnow() + timedelta(hours=2)
    }
    return jwt.encode(payload, secret, algorithm="HS256")


def verify_jwt(token):
    """Verify a JWT token and return the user if valid."""
    secret = os.getenv("SECRET_KEY", "super-secret-key")
    try:
        data = jwt.decode(token, secret, algorithms=["HS256"])
        return User.query.get(data["user_id"])
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def jwt_or_login_required(f):
    """
    A decorator that allows access if:
      - the user is logged in via Flask-Login session, OR
      - a valid JWT token is provided in the Authorization header
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # If user is already logged in (cookie/session)
        if current_user.is_authenticated:
            return f(*args, **kwargs)

        # Try JWT token
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
            user = verify_jwt(token)
            if user:
                return f(*args, **kwargs)

        # Otherwise reject
        return jsonify({"error": "Authentication required"}), 403

    return decorated_function

