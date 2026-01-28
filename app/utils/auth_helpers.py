from functools import wraps
from flask import request, jsonify, g
import jwt, os
from app.extensions import mongo
from bson import ObjectId

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")

from flask import request

from functools import wraps
from flask import jsonify, g
from app.utils.auth_helpers import jwt_required

#fix
def role_required(role_name):
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


def admin_required(fn):
    @wraps(fn)
    @jwt_required()
    def wrapper(*args, **kwargs):
        user = g.get("user")
        if not user or user.get("role") != "admin":
            return jsonify({"error": "Admin access required"}), 403
        return fn(*args, **kwargs)
    return wrapper
