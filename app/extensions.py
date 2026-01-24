# app/extensions.py
from flask_bcrypt import Bcrypt
from flask_mail import Mail

bcrypt = Bcrypt()
mail = Mail()

from flask_socketio import SocketIO

socketio = SocketIO(cors_allowed_origins="*")
