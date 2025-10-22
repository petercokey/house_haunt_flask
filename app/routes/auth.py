from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from app.models import User
from app import db
from app.extensions import bcrypt
from flask_jwt_extended import (
    create_access_token,
    jwt_required,
    get_jwt_identity,
    verify_jwt_in_request,
)
from functools import wraps
from flask_jwt_extended import create_access_token, set_access_cookies
from datetime import timedelta

# Create Blueprint
bp = Blueprint("auth", __name__, url_prefix="/api/auth")


# === Hybrid Auth Helper (Session or JWT) ===
def jwt_or_login_required(role=None):
    """
    Allow access if user is logged in (Flask-Login)
    OR provides a valid JWT.
    Optionally checks role.
    """
    def decorator(fn):
        @wraps(fn)
        def wrapper(*args, **kwargs):
            # Case 1: Flask-Login session
            if current_user and not current_user.is_anonymous:
                if role and current_user.role != role:
                    return jsonify({"error": "Access denied: wrong role"}), 403
                return fn(*args, **kwargs)

            # Case 2: JWT token
            try:
                verify_jwt_in_request()
                identity = get_jwt_identity()
                if role and identity.get("role") != role:
                    return jsonify({"error": "Access denied: wrong role"}), 403
            except Exception:
                return jsonify({"error": "Unauthorized"}), 401

            return fn(*args, **kwargs)
        return wrapper
    return decorator


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
    """Logs in an existing user (supports both Flask-Login and JWT)."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not bcrypt.check_password_hash(user.password, password):  # 👈 changed here
        return jsonify({"error": "Invalid credentials"}), 401

    # Flask-Login session (for browsers)
    login_user(user)

    # JWT token (for APIs or blocked cookies)
    access_token = create_access_token(
        identity={"id": user.id, "role": user.role},
        expires_delta=timedelta(days=1)
    )

    return jsonify({
        "message": "Login successful",
        "token": access_token,
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "credits": user.credits
        }
    }), 200


# === LOGOUT ===
@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    """Logs out the current user."""
    logout_user()
    return jsonify({"message": "Logout successful"}), 200


# === CURRENT USER (works with JWT or session) ===
@bp.route("/me", methods=["GET"])
@jwt_or_login_required()
def get_current_user():
    """Fetch the currently logged-in user via Flask-Login or JWT."""
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


# === ADMIN LOGIN ===
@bp.route("/admin/login", methods=["POST"])
def admin_login():
    """Logs in an admin user."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_admin:
        return jsonify({"error": "Access denied: Not an admin"}), 403

    login_user(user)
    token = create_access_token(identity={"id": user.id, "role": user.role})

    return jsonify({
        "message": "Admin logged in successfully",
        "token": token,
        "user": {"id": user.id, "email": user.email}
    }), 200