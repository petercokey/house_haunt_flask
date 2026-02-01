from flask import Flask, jsonify, send_from_directory, request 
from flask_cors import CORS
from datetime import timedelta, datetime
from werkzeug.security import generate_password_hash
import os
from app.extensions import mongo, bcrypt, mail, socketio


from flask import Flask, jsonify, send_from_directory, request
from flask_cors import CORS
from datetime import timedelta, datetime
from werkzeug.security import generate_password_hash
import os

from app.extensions import mongo, bcrypt, mail, socketio


def create_app():
    app = Flask(__name__)

    # ===============================
    # BASIC CONFIG
    # ===============================
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key")

    app.config["MONGO_URI"] = os.getenv(
        "MONGO_URI",
        "mongodb+srv://petercokey96_db_user:BURCwBViMbuKEuRh@cluster0.7fpmm0p.mongodb.net/househaunt?retryWrites=true&w=majority"
    )

    # ===============================
    # INIT EXTENSIONS
    # ===============================
    mongo.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)

    socketio.init_app(
        app,
        cors_allowed_origins=[
            "http://localhost:5173",
            "https://house-haunt.netlify.app",
        ],
    )

    # ===============================
    # COOKIES
    # ===============================
    app.config.update(
        SESSION_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    )

    # ===============================
    # MAIL
    # ===============================
    app.config.update(
        MAIL_SERVER="smtp.gmail.com",
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    )

    # ===============================
    # CORS
    # ===============================
    CORS(
        app,
        supports_credentials=True,
        resources={
            r"/api/*": {
                "origins": [
                    "http://localhost:5173",
                    "https://house-haunt.netlify.app",
                ]
            }
        },
    )

    @app.before_request
    def handle_preflight():
        if request.method == "OPTIONS":
            return "", 200

    # ===============================
    # REGISTER BLUEPRINTS (ONLY BLUEPRINTS)
    # ===============================
    from app.routes import (
        auth,
        contact,
        wallet,
        review,
        agent,
        haunter,
        kyc,
        dashboard,
        notifications,
        favorites,
        seed,
        transactions,
        static_files,
        admin,
        haunter_chat,
    )

    blueprints = [
        auth.bp,
        contact.bp,
        wallet.bp,
        review.bp,
        agent.bp,
        haunter.bp,
        kyc.bp,
        dashboard.bp,
        notifications.bp,
        favorites.bp,
        seed.bp,
        transactions.bp,
        static_files.bp,
        admin.bp,
        haunter_chat.bp,
    ]

    for bp in blueprints:
        app.register_blueprint(bp)

    # ===============================
    # IMPORT SOCKET EVENTS (NO BLUEPRINT)
    # ===============================
    from app.routes import chat  # noqa: F401

    # ===============================
    # DEFAULT ADMIN
    # ===============================
    create_default_admin(mongo)

    # ===============================
    # HEALTH ROUTES
    # ===============================
    @app.route("/api/ping")
    def ping():
        return jsonify({"message": "pong"}), 200

    @app.route("/")
    def home():
        return jsonify({"status": "House Haunt backend is live!"}), 200

    @app.route("/uploads/<path:filename>")
    def serve_upload(filename):
        upload_folder = os.path.join(app.root_path, "uploads")
        return send_from_directory(upload_folder, filename)

    return app


def create_default_admin(mongo):
    admin_email = "admin@househaunt.com"

    if mongo.db.users.find_one({"email": admin_email}):
        return

    mongo.db.users.insert_one({
        "username": "admin",
        "email": admin_email,
        "password": generate_password_hash("SuperSecret123!"),
        "role": "admin",
        "created_at": datetime.utcnow(),
    })
