from flask import Blueprint, request, jsonify, g, make_response
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
import jwt
import os
import secrets

from app.extensions import mongo
from app.utils.auth_helpers import jwt_required

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
FRONTEND_URL = os.getenv("FRONTEND_URL")
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
EMAIL_FROM = os.getenv("EMAIL_FROM")

# ============================
# REGISTER
# ============================
@bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}

    if not data.get("email") or not data.get("password"):
        return jsonify({"error": "Missing fields"}), 400

    if mongo.db.users.find_one({"email": data["email"]}):
        return jsonify({"error": "Email already registered"}), 409

    user = {
        "username": data.get("username", data["email"].split("@")[0]),
        "email": data["email"],
        "password": generate_password_hash(data["password"]),
        "role": data.get("role", "haunter"),
        "created_at": datetime.utcnow(),
    }

    mongo.db.users.insert_one(user)
    return jsonify({"message": "User registered"}), 201


# ============================
# LOGIN (COOKIE-BASED)
# ============================
@bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}

    user = mongo.db.users.find_one({"email": data.get("email")})
    if not user or not check_password_hash(user["password"], data.get("password")):
        return jsonify({"error": "Invalid credentials"}), 401

    token = jwt.encode(
        {
            "sub": str(user["_id"]),
            "role": user["role"],
            "exp": datetime.utcnow() + timedelta(hours=24),
        },
        SECRET_KEY,
        algorithm=ALGORITHM,
    )

    resp = make_response(jsonify({
        "message": "Login successful",
        "user": {
            "id": str(user["_id"]),
            "username": user.get("username"),
            "email": user.get("email"),
            "role": user.get("role"),
        }
    }))

    cookie_name = f"{user['role']}_token"

    resp.set_cookie(
        cookie_name,
        token,
        httponly=True,
        secure=True,
        samesite="None",
        path=f"/api/{user['role']}",
        max_age=86400
    )

    return resp


# ============================
# ME
# ============================
@bp.route("/me", methods=["GET"])
@jwt_required()
def me():
    return jsonify({
        "id": str(g.user["_id"]),
        "email": g.user["email"],
        "role": g.user["role"],
    })


# ============================
# LOGOUT
# ============================
@bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    role = g.user["role"]
    resp = make_response(jsonify({"message": "Logged out"}))
    resp.delete_cookie(f"{role}_token", path=f"/api/{role}")
    return resp


# ============================
# FORGOT PASSWORD
# ============================
@bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    email = (request.get_json(silent=True) or {}).get("email")
    if not email:
        return jsonify({"message": "If the email exists, a reset link has been sent."})

    user = mongo.db.users.find_one({"email": email})
    if not user:
        return jsonify({"message": "If the email exists, a reset link has been sent."})

    token = secrets.token_urlsafe(32)

    mongo.db.password_resets.insert_one({
        "user_id": user["_id"],
        "token": token,
        "expires_at": datetime.utcnow() + timedelta(minutes=30),
        "used": False
    })

    reset_link = f"{FRONTEND_URL}/reset-password/{token}"

    requests.post(
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {RESEND_API_KEY}",
            "Content-Type": "application/json",
        },
        json={
            "from": EMAIL_FROM,
            "to": [email],
            "subject": "Reset your password",
            "html": f"<p><a href='{reset_link}'>Reset Password</a></p>"
        }
    )

    return jsonify({"message": "If the email exists, a reset link has been sent."})


# ============================
# RESET PASSWORD
# ============================
@bp.route("/reset-password/<token>", methods=["POST"])
def reset_password(token):
    password = (request.get_json(silent=True) or {}).get("password")
    if not password or len(password) < 6:
        return jsonify({"error": "Password too short"}), 400

    record = mongo.db.password_resets.find_one({
        "token": token,
        "used": False,
        "expires_at": {"$gt": datetime.utcnow()}
    })

    if not record:
        return jsonify({"error": "Invalid or expired token"}), 400

    mongo.db.users.update_one(
        {"_id": record["user_id"]},
        {"$set": {"password": generate_password_hash(password)}}
    )

    mongo.db.password_resets.update_one(
        {"_id": record["_id"]},
        {"$set": {"used": True}}
    )

    return jsonify({"message": "Password reset successful"})
