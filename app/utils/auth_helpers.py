# app/utils/auth_helpers.py
from functools import wraps
from flask import request, jsonify, g
import jwt, os
from app.models import User

# 🔹 Secret key for JWT decoding
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")


# ==========================================================
# 🔹 Core JWT Authentication Decorator
# ==========================================================
def jwt_required():
    """
    Ensure the request includes a valid JWT token.
    Decodes the token and attaches the user object to `g.user`.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = request.cookies.get("access_token_cookie")

            if not token:
                return jsonify({"error": "Missing authentication token"}), 401

            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                user = User.query.get(payload.get("user_id"))
                if not user:
                    return jsonify({"error": "User not found"}), 404

                g.user = user
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 401

            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ==========================================================
# 🔹 Role-based Access Control Decorator
# ==========================================================
def role_required(role_name):
    """
    Requires a valid JWT and checks that the user has the given role.
    Example:
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

            if user.role != role_name:
                return jsonify({"error": f"Access denied. Requires '{role_name}' role."}), 403

            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ==========================================================
# 🔹 Utility: get_authenticated_user()
# ==========================================================
def get_authenticated_user():
    """
    Returns the authenticated user if the JWT is valid.
    Can be used manually inside routes instead of decorators.
    """
    token = request.cookies.get("access_token_cookie")
    if not token:
        return None

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        return User.query.get(payload.get("user_id"))
    except Exception:
        return None
