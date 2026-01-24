from functools import wraps
from flask import request, jsonify, g
import jwt, os
from app.extensions import mongo
from bson import ObjectId

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")

def jwt_required():
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            token = request.cookies.get("access_token_cookie")
            if not token:
                return jsonify({"error": "Missing authentication token"}), 401

            try:
                payload = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
                user_id = payload.get("user_id")
                user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
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
