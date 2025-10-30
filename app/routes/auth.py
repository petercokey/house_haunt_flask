from flask import Blueprint, request, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from datetime import timedelta
from functools import wraps
from app.models import User
from app import db
from app.extensions import bcrypt
from app.utils.auth_helpers import jwt_or_login_required
from flask_jwt_extended import (
    create_access_token,
    get_jwt_identity,
    verify_jwt_in_request,
    set_access_cookies,
    unset_jwt_cookies,
)


# Blueprint
bp = Blueprint("auth", __name__, url_prefix="/api/auth")




# === Health Check ===
@bp.route("/ping")
def ping():
    return jsonify({"message": "auth blueprint active!"}), 200


# === REGISTER ===
@bp.route("/register", methods=["POST"])
def register():
    """Registers a new user (haunter or owner)."""
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
    """Login that sets JWT in cookies (Render + Netlify safe)."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials"}), 401

    # Flask-Login session (for browser use)
    login_user(user)

    # JWT cookie
    access_token = create_access_token(
        identity={"id": user.id, "role": user.role},
        expires_delta=timedelta(days=1)
    )

    response = jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "credits": user.credits
        }
    })
    set_access_cookies(response, access_token)
    return response, 200


# === LOGOUT ===
@bp.route("/logout", methods=["POST"])
def logout():
    """Clears the JWT cookie and Flask session."""
    logout_user()
    response = jsonify({"message": "Logout successful"})
    unset_jwt_cookies(response)
    return response, 200


# === CURRENT USER (JWT or Flask session) ===
@bp.route("/me", methods=["GET"])
@jwt_or_login_required()
def get_current_user():
    """Fetch currently logged-in user."""
    try:
        if current_user and not current_user.is_anonymous:
            user = current_user
        else:
            verify_jwt_in_request()
            identity = get_jwt_identity()
            user = User.query.get(identity["id"])
    except Exception:
        return jsonify({"error": "Unauthorized"}), 401

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "credits": user.credits
    }), 200
