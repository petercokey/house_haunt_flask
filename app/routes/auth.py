from flask import Blueprint, request, jsonify
from werkzeug.security import check_password_hash  # (still imported, but no longer used)
from flask_login import login_user, logout_user, login_required, current_user
from sqlalchemy.exc import IntegrityError
from app.models import User
from app import db
from app.extensions import bcrypt

# Create Blueprint
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

    # Check if user already exists
    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already exists."}), 400

    # Hash password
    hashed_pw = bcrypt.generate_password_hash(password).decode("utf-8")

    # Create and store user
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
    """Logs in an existing user."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    user = User.query.filter_by(email=email).first()

    # ✅ FIX: use bcrypt to verify the password (not werkzeug)
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials"}), 401

    login_user(user)  # Stores user in session

    return jsonify({
        "message": "Login successful",
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


# === CURRENT USER ===
@bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    """Fetch the currently logged-in user."""
    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "credits": current_user.credits
    }), 200


# === ADMIN LOGIN ===
@bp.route("/admin/login", methods=["POST"])
def admin_login():
    """Logs in an admin user."""
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    # ✅ FIX: use bcrypt here too
    if not user or not bcrypt.check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_admin:
        return jsonify({"error": "Access denied: Not an admin"}), 403

    login_user(user)
    return jsonify({
        "message": "Admin logged in successfully",
        "user": {"id": user.id, "email": user.email}
    }), 200

