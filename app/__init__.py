# Force rebuild for Render after removing SQLAlchemy references
# app/__init__.py
from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_pymongo import PyMongo
from datetime import timedelta
from flask_bcrypt import Bcrypt
from flask_mail import Mail
import os


mongo = PyMongo()
bcrypt = Bcrypt()
mail = Mail()


def create_app():
    app = Flask(__name__)

    # === Basic Configuration ===
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key")

    # === MongoDB Configuration ===
    app.config["MONGO_URI"] = os.getenv(
        "MONGO_URI",
        "mongodb+srv://petercokey96_db_user:BURCwBViMbuKEuRh@cluster0.7fpmm0p.mongodb.net/househaunt?retryWrites=true&w=majority"
    )
    mongo.init_app(app)

    # === Secure Cookies ===
    app.config.update(
        SESSION_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        PERMANENT_SESSION_LIFETIME=timedelta(days=7),
    )

    # === Mail Configuration ===
    app.config.update(
        MAIL_SERVER="smtp.gmail.com",
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    )

    # === Initialize Extensions ===
    bcrypt.init_app(app)
    mail.init_app(app)

    # === CORS Configuration ===
    CORS(
        app,
        supports_credentials=True,
        resources={
            r"/api/*": {
                "origins": [
                    "http://localhost:5173",
                    "https://house-haunt.netlify.app",
                ],
                "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
                "allow_headers": ["Content-Type", "Authorization"],
            }
        },
    )

    # === Register Blueprints ===
    from app.routes import (
        auth, contact, wallet, review, agent, haunter, kyc,
        dashboard, notifications, favorites, seed, transactions
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
        transactions.bp
    ]

    for bp in blueprints:
        app.register_blueprint(bp)

    # === Health Check Routes ===
    @app.route("/api/ping")
    def ping():
        return jsonify({"message": "pong"}), 200

    @app.route("/")
    def home():
        return jsonify({"status": "House Haunt backend is live and running!"}), 200

    @app.route("/uploads/<path:filename>")
    def serve_upload(filename):
        upload_folder = os.path.join(app.root_path, "uploads")
        return send_from_directory(upload_folder, filename)
    

    # force rebuild comment

    app.mongo = mongo

    return app
