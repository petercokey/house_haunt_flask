# app/utils/auth_helpers.py
from functools import wraps
from flask import request, jsonify, g
import jwt
import os
from app.extensions import mongo
from bson import ObjectId

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")
ALGORITHM = "HS256"


def jwt_required():
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            auth_header = request.headers.get("Authorization")

            if not auth_header or not auth_header.startswith("Bearer "):
                return jsonify({"error": "Missing or invalid token"}), 401

            token = auth_header.split(" ")[1]

            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

                user_id = payload.get("user_id")
                if not user_id:
                    return jsonify({"error": "Invalid token payload"}), 401

                user = mongo.db.users.find_one(
                    {"_id": ObjectId(user_id)},
                    {"password": 0}
                )

                if not user:
                    return jsonify({"error": "User not found"}), 401

                g.user = user

            except jwt.ExpiredSignatureError:
                return jsonify({"error": "Token expired"}), 401
            except jwt.InvalidTokenError:
                return jsonify({"error": "Invalid token"}), 401

            return fn(*args, **kwargs)
        return wrapper
    return decorator


def role_required(role_name):
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
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


def admin_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        user = g.get("user")

        if not user or user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403

        return fn(*args, **kwargs)
    return wrapper
