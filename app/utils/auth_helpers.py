from flask import request, current_app
from bson import ObjectId
import jwt

from app.extensions import mongo

def decode_socket_token():
    auth = request.auth or {}
    token = auth.get("token")

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],
            algorithms=["HS256"]
        )
        return mongo.db.users.find_one(
            {"_id": ObjectId(payload["user_id"])}
        )
    except Exception:
        return None


