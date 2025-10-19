from flask import Flask, jsonify
from flask_cors import CORS
import os

# Import initialized extensions from app/extensions.py
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

    # === Mail Configuration ===
    app.config.update(
        MAIL_SERVER="smtp.gmail.com",
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),  # Gmail address
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),  # App password
    )

    # === Enable CORS for frontend access ===
    from flask_cors import CORS

    CORS(app, resources={
    r"/api/*": {
        "origins": [
            "http://localhost:5173",
            "https://house-haunt.netlify.app"
        ],
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"],
        "supports_credentials": True
    }
    })

    # Allow secure cookies across domains (Render + Netlify use HTTPS)
    app.config.update(
    SESSION_COOKIE_SAMESITE="None",
    SESSION_COOKIE_SECURE=True
    )


    # === Initialize extensions ===
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

    # === Basic Health Routes ===
    @app.route("/api/ping")
    def ping():
        return jsonify({"message": "pong"}), 200

    @app.route("/")
    def home():
        return jsonify({"status": "House Haunt backend is live and running!"}), 200

    return app