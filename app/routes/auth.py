# app/routes/auth.py
from flask import Blueprint, request, jsonify, make_response
from sqlalchemy.exc import IntegrityError
from datetime import datetime, timedelta
from app.models import User
from app import db
from app.extensions import bcrypt
from app.utils.auth_helpers import jwt_required
import jwt, os

bp = Blueprint("auth", __name__, url_prefix="/api/auth")
SECRET_KEY = os.getenv("SECRET_KEY", "super-secret-key")

# === Health Check ===
@bp.route("/ping")
def ping():
    return jsonify({"message": "auth blueprint active!"}), 200


# === REGISTER ===
@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "haunter")

    if not all([username, email, password]):
        return jsonify({"error": "All fields are required."}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists."}), 400

    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")
    user = User(username=username, email=email, password=hashed_pw, role=role)
    db.session.add(user)
    db.session.commit()

    return jsonify({
        "message": "Registration successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 201


# === LOGIN ===
@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Email and password required"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials"}), 401

    payload = {
        "user_id": user.id,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(days=1)
    }
    token = jwt.encode(payload, SECRET_KEY, algorithm="HS256")

    resp = make_response(jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "credits": user.credits
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


# === LOGOUT ===
@bp.route("/logout", methods=["POST"])
def logout():
    resp = jsonify({"message": "Logout successful"})
    resp.set_cookie("access_token_cookie", "", expires=0, path="/")
    return resp, 200


# === CURRENT USER (JWT protected) ===
@bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    from flask import g
    user = g.user
    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "credits": user.credits
    }), 200
