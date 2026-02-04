from functools import wraps
from flask import request, jsonify, g
import jwt
from bson import ObjectId
from datetime import datetime
import os
from app.extensions import mongo

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY not set")


def _get_token_from_cookies():
    return (
        request.cookies.get("agent_token")
        or request.cookies.get("haunter_token")
        or request.cookies.get("admin_token")
    )


def jwt_required():
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = _get_token_from_cookies()
            if not token:
                return jsonify({"error": "Authentication required"}), 401

            try:
                payload = jwt.decode(
                    token,
                    SECRET_KEY,
                    algorithms=[ALGORITHM]
                )
                user_id = payload.get("sub")
                user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
                if not user:
                    return jsonify({"error": "Invalid user"}), 401

                g.user = user
            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Session expired"}), 401
            except Exception:
                return jsonify({"error": "Invalid token"}), 401

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def role_required(role):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            if g.user.get("role") != role:
                return jsonify({"error": "Access denied"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if g.user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper


