from flask import Blueprint, request, jsonify, g
from werkzeug.security import generate_password_hash, check_password_hash
import jwt
from datetime import datetime, timedelta
from app.extensions import mongo, mail
from app.utils.auth_helpers import jwt_required
import os
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
    data = request.get_json(silent=True) or {}
    email = data.get("email")

    if not email:
        return jsonify({"error": "Email is required"}), 400

    user = mongo.db.users.find_one({"email": email})

    # Anti user-enumeration
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
        "used": False,
        "created_at": datetime.utcnow(),
    })

    frontend_url = os.getenv("FRONTEND_URL")
    resend_api_key = os.getenv("RESEND_API_KEY")
    email_from = os.getenv("EMAIL_FROM")

    if not all([frontend_url, resend_api_key, email_from]):
        raise RuntimeError("Missing Resend environment variables")

    reset_link = f"{frontend_url}/reset-password/{token}"

    response = requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {resend_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": email_from,
            "to": [email],
            "subject": "Reset your HouseHaunt password",
            "html": f"""
                <p>Hello {user.get("username")},</p>

                <p>Click the link below to reset your password:</p>

                <p><a href="{reset_link}">Reset Password</a></p>

                <p>This link expires in 30 minutes.</p>

                <p>If you did not request this, ignore this email.</p>
            """
        }
    )

    if response.status_code >= 400:
        raise RuntimeError(f"Resend error: {response.text}")

    return jsonify({
        "message": "If the email exists, a reset link has been sent."
    }), 200


@bp.route("/reset-password/<token>", methods=["POST"])
def reset_password(token):
    data = request.get_json(silent=True) or {}
    new_password = data.get("password")

    if not new_password or len(new_password) < 6:
        return jsonify({
            "error": "Password must be at least 6 characters"
        }), 400

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
        {"$set": {
            "password": hashed_password,
            "password_updated_at": datetime.utcnow()
        }}
    )

    mongo.db.password_resets.update_one(
        {"_id": record["_id"]},
        {"$set": {"used": True}}
    )

    return jsonify({
        "message": "Password reset successful. Please login."
    }), 200