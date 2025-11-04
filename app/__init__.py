from flask import Flask, jsonify, send_from_directory
from flask_cors import CORS
from flask_jwt_extended import JWTManager
import os
from datetime import timedelta

# Import initialized extensions
from app.extensions import db, bcrypt, mail, login_manager
from flask_migrate import Migrate


def create_app():
    app = Flask(__name__)

    # === Basic Configuration ===
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///househaunt.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # === JWT Configuration (cookies-based auth) ===
    # === JWT Configuration (cookies-based auth) ===
    app.config["JWT_SECRET_KEY"] = os.getenv("JWT_SECRET_KEY", "super-secret-jwt-key")
    app.config["JWT_TOKEN_LOCATION"] = ["cookies"]
    app.config["JWT_ACCESS_COOKIE_NAME"] = "access_token_cookie"
    app.config["JWT_COOKIE_SECURE"] = True           # required for HTTPS (Render)
    app.config["JWT_COOKIE_SAMESITE"] = "None"       # allows Netlify + Render cross-site cookies
    app.config["JWT_COOKIE_HTTPONLY"] = True         # JS can't read cookie
    app.config["JWT_COOKIE_CSRF_PROTECT"] = False    # simplify for now
    app.config["JWT_ACCESS_TOKEN_EXPIRES"] = timedelta(days=1)
    app.config["JWT_COOKIE_DOMAIN"] = os.getenv("JWT_COOKIE_DOMAIN", "house-haunt-flask.onrender.com")

    jwt = JWTManager(app)

    # === Mail Configuration ===
    app.config.update(
        MAIL_SERVER="smtp.gmail.com",
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),
    )

    # === Secure Session Cookies ===
    app.config.update(
        SESSION_COOKIE_SAMESITE="None",
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        REMEMBER_COOKIE_SAMESITE="None",
        REMEMBER_COOKIE_SECURE=True,
    )

    # === CORS Configuration (allow frontend access) ===
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

    # === Initialize Extensions ===
    db.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    login_manager.init_app(app)
    migrate = Migrate(app, db)

    # === Flask-Login Configuration ===
    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    login_manager.login_view = "auth.login"
    login_manager.login_message_category = "info"

    # === Register Blueprints ===
    from app.routes import (
        auth, contact, wallet, review, agent, haunter, kyc,
        dashboard, notifications, favorites, seed
    )

    app.register_blueprint(auth.bp)
    app.register_blueprint(contact.bp)
    app.register_blueprint(wallet.bp)
    app.register_blueprint(review.bp)
    app.register_blueprint(agent.bp)
    app.register_blueprint(haunter.bp)
    app.register_blueprint(kyc.bp)
    app.register_blueprint(dashboard.bp)
    app.register_blueprint(notifications.bp)
    app.register_blueprint(favorites.bp)
    app.register_blueprint(seed.bp)

    # === Health Check Routes ===
    @app.route("/api/ping")
    def ping():
        return jsonify({"message": "pong"}), 200

    @app.route("/")
    def home():
        return jsonify({"status": "House Haunt backend is live and running!"}), 200
    
    # === Serve uploaded files (for image display) ===
    @app.route("/uploads/<path:filename>")
    def serve_upload(filename):
        upload_folder = os.path.join(app.root_path, "uploads")
        return send_from_directory(upload_folder, filename)


    return app
