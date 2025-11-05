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


# === LOGIN (debug/isolation) ===
@bp.route("/login", methods=["POST"])
def login():
    """
    Debug login: step-by-step checks to isolate process crash.
    - Logs progress to Render logs.
    - Avoids calling potentially crashing helpers until proven safe.
    """
    from flask import current_app
    current_app.logger.info("[LOGIN DEBUG] start")

    data = request.get_json(silent=True) or {}
    email = data.get("email")
    password = data.get("password")
    current_app.logger.info("[LOGIN DEBUG] received payload email=%s", bool(email))

    # Basic validation
    if not email or not password:
        current_app.logger.info("[LOGIN DEBUG] missing credentials")
        return jsonify({"error": "Missing email or password"}), 400

    # Step 1: find user
    try:
        user = User.query.filter_by(email=email).first()
        current_app.logger.info("[LOGIN DEBUG] user lookup done user_exists=%s", bool(user))
    except Exception as e:
        current_app.logger.exception("[LOGIN DEBUG] error during DB lookup")
        return jsonify({"error": "Server error (lookup)"}), 500

    if not user:
        current_app.logger.info("[LOGIN DEBUG] invalid credentials - no user")
        return jsonify({"error": "Invalid credentials"}), 401

    # Step 2: password check (catch low-level exceptions)
    try:
        pw_ok = False
        # call bcrypt check in try/except
        try:
            pw_ok = bcrypt.check_password_hash(user.password, password)
            current_app.logger.info("[LOGIN DEBUG] bcrypt check completed result=%s", pw_ok)
        except Exception as e_inner:
            current_app.logger.exception("[LOGIN DEBUG] bcrypt raised")
            return jsonify({"error": "Server error (password check)"}), 500

        if not pw_ok:
            current_app.logger.info("[LOGIN DEBUG] invalid credentials - wrong password")
            return jsonify({"error": "Invalid credentials"}), 401

    except Exception as e:
        current_app.logger.exception("[LOGIN DEBUG] unexpected error in password step")
        return jsonify({"error": "Server error (password)"}), 500

    # Step 3: create token (pure python)
    try:
        access_token = create_access_token(
            identity={"id": user.id, "role": user.role},
            expires_delta=timedelta(days=1)
        )
        current_app.logger.info("[LOGIN DEBUG] token created len=%d", len(access_token))
    except Exception as e:
        current_app.logger.exception("[LOGIN DEBUG] token creation failed")
        return jsonify({"error": "Server error (token)"}), 500

    # Step 4: build response JSON (safe)
    response = jsonify({
        "message": "Login debug OK",
        "user": {
            "id": user.id,
            "username": user.username,
            "role": user.role
        },
        # include token here ONLY for debugging (temporary)
        "debug_access_token_present": bool(access_token)
    })

    # DO NOT set cookie yet. Log and return.
    current_app.logger.info("[LOGIN DEBUG] returning response WITHOUT setting cookie")
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
