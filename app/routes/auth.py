# app/routes/auth.py
from flask import Blueprint, request, jsonify, make_response, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from bson import ObjectId
from app import mongo
from app.utils.auth_helpers import jwt_required
import os
from flask_jwt_extended import (
    jwt_required,
    get_jwt,
    create_access_token,
    set_access_cookies,
    unset_jwt_cookies,
    JWTManager
)

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")

jwt = JWTManager()
# ==========================================================
# 🔹 Register
# ==========================================================
@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Missing required fields"}), 400

    if mongo.db.users.find_one({"email": data["email"]}):
        return jsonify({"error": "Email already registered"}), 409

    hashed_password = generate_password_hash(data["password"])

    user = {
        "username": data.get("username", data["email"].split("@")[0]),
        "email": data["email"],
        "password": hashed_password,
        "role": data.get("role", "haunter"),
        "created_at": datetime.utcnow(),
    }

    result = mongo.db.users.insert_one(user)
    user["_id"] = result.inserted_id

    return jsonify({
        "message": "User registered successfully",
        "user": {"id": str(user["_id"]), "email": user["email"], "role": user["role"]}
    }), 201


# ==========================================================
# 🔹 Login
# ==========================================================
@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    if not data or not data.get("email") or not data.get("password"):
        return jsonify({"error": "Missing credentials"}), 400

    user = mongo.db.users.find_one({"email": data["email"]})
    if not user:
        return jsonify({"error": "Invalid email or password"}), 401

    try:
        valid_password = check_password_hash(user["password"], data["password"])
    except ValueError:
        return jsonify({"error": "Invalid password format. Please reset your password."}), 400

    if not valid_password:
        return jsonify({"error": "Invalid email or password"}), 401

    token = jwt.encode({
        "user_id": str(user["_id"]),
        "exp": datetime.utcnow() + timedelta(hours=24)
    }, SECRET_KEY, algorithm="HS256")

    response_data = {
        "message": "Login successful",
        "token": token,
        "user": {  # <-- add this
            "id": str(user["_id"]),
            "username": user.get("username"),
            "email": user.get("email"),
            "role": user.get("role")
        }
    }

    response = make_response(jsonify(response_data), 200)
    response.set_cookie(
        "access_token_cookie",
        token,
        httponly=True,
        samesite="None",
        secure=True,
        max_age=24 * 3600
    )
    return response



# ==========================================================
# 🔹 Get current user
# ==========================================================
@bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user = mongo.db.users.find_one({"_id": ObjectId(g.user["_id"])})
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": str(user["_id"]),
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role"),
    }), 200


# ==========================================================
# 🔹 Logout
@bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    jti = get_jwt()["jti"]  # JWT unique identifier
    # Store revoked token in MongoDB
    mongo.db.revoked_tokens.insert_one({"jti": jti, "revoked_at": datetime.utcnow()})

    # Delete cookie for frontend
    response = jsonify({"message": "Logged out successfully"})
    unset_jwt_cookies(response)  # Removes access & refresh cookies if used
    return response, 200

# =========================
# JWT blocklist check
# =========================
@jwt.token_in_blocklist_loader
def check_if_token_revoked(jwt_header, jwt_payload):
    jti = jwt_payload["jti"]
    token = mongo.db.revoked_tokens.find_one({"jti": jti})
    return token is not None

# =========================
# Example /auth/me route
# =========================
@bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    user_id = g.user["_id"]
    user = mongo.db.users.find_one({"_id": user_id})
    if not user:
        return jsonify(None), 404

    return jsonify({
        "id": str(user["_id"]),
        "username": user["username"],
        "email": user["email"],
        "role": user.get("role", "haunter"),
        "created_at": user.get("created_at")
    }), 200
