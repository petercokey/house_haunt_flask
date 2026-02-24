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
# JOIN CHAT ROOM
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

    emit("joined_chat", {"chat_id": str(chat_oid)})


# ===============================
# SEND MESSAGE
# ===============================

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

    now = datetime.utcnow()

    message = {
        "chat_id": chat_oid,
        "sender_id": user["_id"],
        "sender_role": user["role"],
        "content": content,
        "created_at": now,
        "delivered_at": None,
        "read_at": None,
    }

    result = mongo.db.messages.insert_one(message)
    message_id = result.inserted_id

    emit(
        "receive_message",
        {
            "message_id": str(message_id),
            "chat_id": str(chat_oid),
            "sender": {
                "id": str(user["_id"]),
                "role": user["role"],
                "username": user.get("username"),
            },
            "content": content,
            "created_at": now.isoformat(),
            "delivered_at": None,
            "read_at": None,
        },
        room=str(chat_oid)
    )


# ===============================
# MARK MESSAGE DELIVERED
# ===============================

@socketio.on("message_delivered")
def mark_message_delivered(data):
    user = decode_socket_token()
    if not user:
        return

    message_oid = safe_object_id(data.get("message_id"))
    if not message_oid:
        return

    now = datetime.utcnow()

    result = mongo.db.messages.update_one(
        {
            "_id": message_oid,
            "sender_id": {"$ne": user["_id"]},
            "delivered_at": None
        },
        {
            "$set": {"delivered_at": now}
        }
    )

    if result.modified_count > 0:
        message = mongo.db.messages.find_one({"_id": message_oid})
        emit(
            "message_status_update",
            {
                "message_id": str(message_oid),
                "status": "delivered",
                "delivered_at": now.isoformat()
            },
            room=str(message["chat_id"])
        )


# ===============================
# MARK CHAT AS READ (BULK)
# ===============================

@socketio.on("mark_chat_read")
def mark_chat_read(data):
    user = decode_socket_token()
    if not user:
        return

    chat_oid = safe_object_id(data.get("chat_id"))
    if not chat_oid:
        return

    now = datetime.utcnow()

    mongo.db.messages.update_many(
        {
            "chat_id": chat_oid,
            "sender_id": {"$ne": user["_id"]},
            "read_at": None
        },
        {
            "$set": {
                "read_at": now,
                "delivered_at": now
            }
        }
    )

    emit(
        "chat_read_update",
        {
            "chat_id": str(chat_oid),
            "read_at": now.isoformat()
        },
        room=str(chat_oid)
    )