from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from app.extensions import mongo, mail
from app.utils.auth_helpers import jwt_required
import os
from flask_mail import Message
import secrets

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"

if not SECRET_KEY:
    raise RuntimeError("SECRET_KEY environment variable not set")


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
        "user": {
            "id": str(user["_id"]),
            "email": user["email"],
            "role": user["role"]
        }
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

    


    token = jwt.encode(
        {
            "user_id": str(user["_id"]),
            "exp": datetime.utcnow() + timedelta(hours=24),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    return jsonify({
        "message": "Login successful",
        "token": token,
        "user": {
            "id": str(user["_id"]),
            "username": user.get("username"),
            "email": user.get("email"),
            "role": user.get("role"),
        },
    }), 200


# ==========================================================
# 🔹 Get current user
# ==========================================================
@bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user = g.user

    return jsonify({
        "id": str(user["_id"]),
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role"),
    }), 200



# ==========================================================
# 🔹 Logout (JWT – Stateless)
# ==========================================================
@bp.route("/logout", methods=["POST"])
def logout():
    """
    JWT logout is stateless.
    Frontend must delete the token.
    This endpoint exists for API completeness.
    """
    return jsonify({
        "message": "Logged out successfully. Please delete token on client."
    }), 200

@bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json()
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = mongo.db.users.find_one({"email": email})

    # Always return success (anti-user-enumeration)
    if not user:
        return jsonify({
            "message": "If the email exists, a reset link has been sent."
        }), 200

    token = secrets.token_urlsafe(32)
    expires_at = datetime.utcnow() + timedelta(minutes=30)

    mongo.db.password_resets.insert_one({
        "user_id": user["_id"],
        "token": token,
        "expires_at": expires_at,
        "used": False
    })

    reset_link = f"{os.getenv('FRONTEND_URL')}/reset-password/{token}"

    msg = Message(
        subject="Reset your HouseHaunt password",
        recipients=[email],
        body=f"""
Hello {user.get('username')},

Click the link below to reset your password:
{reset_link}

This link expires in 30 minutes.

If you did not request this, ignore this email.
"""
    )

    mail.send(msg)

    return jsonify({
        "message": "If the email exists, a reset link has been sent."
    }), 200

@bp.route("/reset-password/<token>", methods=["POST"])
def reset_password(token):
    data = request.get_json()
    new_password = data.get("password")

    if not new_password or len(new_password) < 6:
        return jsonify({"error": "Password must be at least 6 characters"}), 400

    record = mongo.db.password_resets.find_one({
        "token": token,
        "used": False,
        "expires_at": {"$gt": datetime.utcnow()}
    })

    if not record:
        return jsonify({"error": "Invalid or expired token"}), 400

    hashed_password = generate_password_hash(new_password)

    mongo.db.users.update_one(
        {"_id": record["user_id"]},
        {"$set": {"password": hashed_password}}
    )

    mongo.db.password_resets.update_one(
        {"_id": record["_id"]},
        {"$set": {"used": True}}
    )

    return jsonify({
        "message": "Password reset successful. Please login."
    }), 200
