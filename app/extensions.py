# app/extensions.py
from flask_pymongo import PyMongo
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_socketio import SocketIO

mongo = PyMongo()
bcrypt = Bcrypt()
mail = Mail()
socketio = SocketIO(cors_allowed_origins="*")
