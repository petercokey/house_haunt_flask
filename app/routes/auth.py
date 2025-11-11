# app/routes/auth.py
from flask import Blueprint, request, jsonify, make_response, current_app, g
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from bson import ObjectId
from app import mongo
from app.utils.auth_helpers import jwt_required
import os

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")


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

    user = {
        "username": data.get("username", data["email"].split("@")[0]),
        "email": data["email"],
        "password": generate_password_hash(data["password"]),
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
    if not user or not check_password_hash(user["password"], data["password"]):
        return jsonify({"error": "Invalid email or password"}), 401

    token = jwt.encode({
        "user_id": str(user["_id"]),
        "exp": datetime.utcnow() + timedelta(hours=24)
    }, SECRET_KEY, algorithm="HS256")

    response = make_response(jsonify({
        "message": "Login successful",
        "token": token
    }), 200)
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
# ==========================================================
@bp.route("/logout", methods=["POST"])
def logout():
    response = make_response(jsonify({"message": "Logged out"}), 200)
    response.delete_cookie("access_token_cookie")
    return response
