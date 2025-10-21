from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_login import LoginManager
from flask_jwt_extended import JWTManager  # ✅ Add this line

# === Initialize extensions globally (no app bound yet) ===
db = SQLAlchemy()
bcrypt = Bcrypt()
mail = Mail()
login_manager = LoginManager()
jwt = JWTManager()  # ✅ Add this line



