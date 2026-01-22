from flask_socketio import join_room, emit
from bson import ObjectId
from datetime import datetime
from app import mongo
from app.extensions import socketio


@socketio.on("join_chat")
def join_chat(data):
    chat_id = data.get("chat_id")

    if not chat_id:
        return

    join_room(chat_id)

@socketio.on("send_message")
def send_message(data):
    chat_id = data.get("chat_id")
    sender_id = data.get("sender_id")
    sender_role = data.get("sender_role")
    content = data.get("content")

    if not all([chat_id, sender_id, sender_role, content]):
        return

    message = {
        "chat_id": ObjectId(chat_id),
        "sender_id": ObjectId(sender_id),
        "sender_role": sender_role,
        "content": content,
        "created_at": datetime.utcnow(),
    }

    mongo.db.messages.insert_one(message)

    emit(
        "receive_message",
        {
            "sender_role": sender_role,
            "content": content,
            "created_at": message["created_at"].isoformat()
        },
        room=chat_id
    )
"""  """