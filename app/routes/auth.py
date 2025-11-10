# app/routes/auth.py
from flask import Blueprint, request, jsonify, make_response, g, current_app
from datetime import datetime, timedelta
from app.extensions import bcrypt
from app.utils.auth_helpers import jwt_required
from bson import ObjectId
import jwt, os

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")


# -----------------------------
# Helper Mongo User model
# -----------------------------
class User:
    @staticmethod
    def create(data):
        return current_app.mongo.db.users.insert_one(data)

    @staticmethod
    def find_by_email(email):
        return current_app.mongo.db.users.find_one({"email": email})

    @staticmethod
    def find_by_id(user_id):
        return current_app.mongo.db.users.find_one({"_id": ObjectId(user_id)})


# -----------------------------
# Health check
# -----------------------------
@bp.route("/ping")
def ping():
    return jsonify({"message": "auth blueprint active!"}), 200


# -----------------------------
# Register
# -----------------------------
@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "haunter")

    if not all([username, email, password]):
        return jsonify({"error": "All fields are required."}), 400

    if User.find_by_email(email):
        return jsonify({"error": "Email already exists."}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
    user_data = {
        "username": username,
        "email": email,
        "password": hashed_pw,
        "role": role,
        "credits": 0,
        "created_at": datetime.utcnow()
    }

    result = User.create(user_data)
    user_id = str(result.inserted_id)

    return jsonify({
        "message": "Registration successful",
        "user": {
            "id": user_id,
            "username": username,
            "email": email,
            "role": role
        }
    }), 201


# -----------------------------
# Login
# -----------------------------
@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = User.find_by_email(email)
    if not user or not bcrypt.check_password_hash(user["password"], password):
        return jsonify({"error": "Invalid credentials"}), 401

    payload = {
        "user_id": str(user["_id"]),
        "role": user.get("role"),
        "exp": datetime.utcnow() + timedelta(days=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    resp = make_response(jsonify({
        "message": "Login successful",
        "user": {
            "id": str(user["_id"]),
            "username": user.get("username"),
            "email": user.get("email"),
            "role": user.get("role"),
            "credits": user.get("credits", 0)
        }
    }))
    resp.set_cookie(
        "access_token_cookie",
        token,
        httponly=True,
        secure=True,
        samesite="None",
        path="/"
    )
    return resp, 200


# -----------------------------
# Logout
# -----------------------------
@bp.route("/logout", methods=["POST"])
def logout():
    resp = jsonify({"message": "Logout successful"})
    resp.set_cookie("access_token_cookie", "", expires=0, path="/")
    return resp, 200


# -----------------------------
# Get Current User
# -----------------------------
@bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user = g.user
    if not user:
        return jsonify({"error": "User not found"}), 404

    return jsonify({
        "id": str(user["_id"]),
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role"),
        "credits": user.get("credits", 0)
    }), 200
