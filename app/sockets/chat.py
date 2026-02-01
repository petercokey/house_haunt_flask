from flask import request, current_app
from flask_socketio import join_room, emit
from bson import ObjectId
from datetime import datetime
import jwt
from app.extensions import socketio, mongo


# ===============================
# HELPERS
# ===============================

def decode_socket_token():
    """
    Extract JWT from Socket.IO auth payload and return user
    """
    auth = request.auth or {}
    token = auth.get("token")

    if not token:
        return None

    try:
        payload = jwt.decode(
            token,
            current_app.config["SECRET_KEY"],  # ✅ CORRECT
            algorithms=["HS256"]
        )

        return mongo.db.users.find_one({
            "_id": ObjectId(payload["user_id"])
        })

    except Exception:
        return None


def safe_object_id(value):
    try:
        return ObjectId(value)
    except Exception:
        return None


def is_chat_participant(chat, user):
    return (
        chat.get("agent_id") == user["_id"] or
        chat.get("haunter_id") == user["_id"]
    )


# ===============================
# SOCKET EVENTS
# ===============================

@socketio.on("join_chat")
def join_chat(data):
    user = decode_socket_token()
    if not user:
        emit("error", {"error": "Unauthorized"})
        return

    chat_oid = safe_object_id(data.get("chat_id"))
    if not chat_oid:
        emit("error", {"error": "Invalid chat id"})
        return

    chat = mongo.db.chats.find_one({"_id": chat_oid})
    if not chat or not is_chat_participant(chat, user):
        emit("error", {"error": "Access denied"})
        return

    join_room(str(chat_oid))

    emit(
        "joined_chat",
        {"chat_id": str(chat_oid)},
        room=str(chat_oid)
    )


@socketio.on("send_message")
def send_message(data):
    user = decode_socket_token()
    if not user:
        emit("error", {"error": "Unauthorized"})
        return

    chat_oid = safe_object_id(data.get("chat_id"))
    content = data.get("content")

    if not chat_oid or not content:
        emit("error", {"error": "Invalid payload"})
        return

    chat = mongo.db.chats.find_one({"_id": chat_oid})
    if not chat or not is_chat_participant(chat, user):
        emit("error", {"error": "Access denied"})
        return

    message = {
        "chat_id": chat_oid,
        "sender_id": user["_id"],
        "sender_role": user["role"],
        "content": content,
        "created_at": datetime.utcnow(),
    }

    mongo.db.messages.insert_one(message)

    emit(
        "receive_message",
        {
            "chat_id": str(chat_oid),
            "sender": {
                "id": str(user["_id"]),
                "role": user["role"],
                "username": user.get("username"),
            },
            "content": content,
            "created_at": message["created_at"].isoformat(),
        },
        room=str(chat_oid)
    )
