from flask import Flask, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from flask_login import LoginManager
from flask_cors import CORS
from flask_mail import Mail
import os
from app.routes import favorites



# Initialize extensions globally
db = SQLAlchemy()
migrate = Migrate()
login_manager = LoginManager()
mail = Mail()

def create_app():
    app = Flask(__name__)

    from flask_cors import CORS



    # Configuration
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "super-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL", "sqlite:///househaunt.db"
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Mail configuration
    app.config.update(
        MAIL_SERVER="smtp.gmail.com",
        MAIL_PORT=587,
        MAIL_USE_TLS=True,
        MAIL_USERNAME=os.getenv("MAIL_USERNAME"),  # Gmail address
        MAIL_PASSWORD=os.getenv("MAIL_PASSWORD"),  # App password
    )

    # Enable CORS for frontend API access

    CORS(app, resources={r"/*": {
    "origins": [
        "http://localhost:5173",
        "https://house-haunt.netlify.app"
    ]
    }})



    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    mail.init_app(app)

    # Import models AFTER db is initialized
    from app.models import User

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    # Import and register blueprints
    from app.routes import (
    auth, contact, wallet, review, agent, haunter, kyc, dashboard, notifications, favorites
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



    # Simple test endpoint
    @app.route("/api/ping")
    def ping():
        return jsonify({"message": "pong"}), 200

    @app.route('/')
    def home():
        return {"status": "House Haunt backend is live and running!"}, 200


    return app
