# app/routes/auth.py
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import login_user, logout_user, login_required
from app.models import User
from app import db
from flask_login import current_user


bp = Blueprint("auth", __name__, url_prefix="/api/auth")
@bp.route("/ping")
def ping():
    return jsonify({"message": "auth blueprint active!"}), 200

# Example route to verify it's working


@bp.route("/signup", methods=["POST"])
def signup():
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role")  # "owner" or "haunter"

    if not all([username, email, password, role]):
        return jsonify({"error": "Missing required fields"}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email already registered"}), 400

    user = User(
        username=username,
        email=email,
        password=generate_password_hash(password),
        role=role
    )
    db.session.add(user)
    db.session.commit()

    return jsonify({"message": "Signup successful"}), 201



@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    if not email or not password:
        return jsonify({"error": "Missing email or password"}), 400

    user = User.query.filter_by(email=email).first()
    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials"}), 401

    login_user(user)  # Flask-Login stores user ID in session cookie

    return jsonify({
        "message": "Login successful",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "credits": user.credits
        }
    }), 200

@bp.route("/logout", methods=["POST"])
@login_required
def logout():
    logout_user()
    return jsonify({"message": "Logout successful"}), 200

@bp.route("/me", methods=["GET"])
@login_required
def get_current_user():
    return jsonify({
        "id": current_user.id,
        "username": current_user.username,
        "email": current_user.email,
        "role": current_user.role,
        "credits": current_user.credits
    }), 200

@bp.route("/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json()
    email = data.get("email")
    password = data.get("password")

    user = User.query.filter_by(email=email).first()

    if not user or not check_password_hash(user.password, password):
        return jsonify({"error": "Invalid credentials"}), 401

    if not user.is_admin:
        return jsonify({"error": "Access denied: Not an admin"}), 403

    login_user(user)
    return jsonify({"message": "Admin logged in successfully", "user": {"id": user.id, "email": user.email}}), 200
