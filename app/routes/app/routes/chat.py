from flask import Blueprint, jsonify, request, g
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

from app.extensions import mongo
from app.utils.auth_helpers import jwt_required

bp = Blueprint("chat", __name__, url_prefix="/api/chats")


# ===============================
# HELPERS
# ===============================
def parse_object_id(value):
    try:
        return ObjectId(value)
    except (InvalidId, TypeError):
        return None


def is_chat_participant(chat, user):
    return (
        chat.get("agent_id") == user["_id"] or
        chat.get("haunter_id") == user["_id"]
    )


# ===============================
# GET USER CHATS (AGENT + HAUNTER)
# ===============================
@bp.route("", methods=["GET"])
@jwt_required()
def get_user_chats():
    user = g.user
    role = user["role"]

    query = (
        {"agent_id": user["_id"]}
        if role == "agent"
        else {"haunter_id": user["_id"]}
    )

    chats = mongo.db.chats.find(query).sort("created_at", -1)

    results = []
    for chat in chats:
        other_user_id = (
            chat["haunter_id"] if role == "agent" else chat["agent_id"]
        )

        other_user = mongo.db.users.find_one(
            {"_id": other_user_id},
            {"username": 1, "email": 1, "role": 1}
        )

        results.append({
            "chat_id": str(chat["_id"]),
            "created_at": chat["created_at"],
            "participant": {
                "id": str(other_user["_id"]) if other_user else None,
                "username": other_user.get("username") if other_user else None,
                "email": other_user.get("email") if other_user else None,
                "role": other_user.get("role") if other_user else None,
            }
        })

    return jsonify({
        "total": len(results),
        "chats": results
    }), 200


# ===============================
# CHAT MESSAGES (GET / POST)
# ===============================
@bp.route("/<chat_id>/messages", methods=["GET", "POST"])
@jwt_required()
def chat_messages(chat_id):
    chat_oid = parse_object_id(chat_id)
    if not chat_oid:
        return jsonify({"error": "Invalid chat id"}), 400

    chat = mongo.db.chats.find_one({"_id": chat_oid})
    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    if not is_chat_participant(chat, g.user):
        return jsonify({"error": "Not authorized for this chat"}), 403

    # -----------------------
    # SEND MESSAGE
    # -----------------------
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        content = data.get("content")

        if not content:
            return jsonify({"error": "Message content required"}), 400

        mongo.db.messages.insert_one({
            "chat_id": chat_oid,
            "sender_id": g.user["_id"],
            "sender_role": g.user["role"],
            "content": content,
            "created_at": datetime.utcnow(),
        })

        return jsonify({"message": "Message sent"}), 201

    # -----------------------
    # GET MESSAGES
    # -----------------------
    messages = mongo.db.messages.find(
        {"chat_id": chat_oid}
    ).sort("created_at", 1)

    return jsonify({
        "messages": [
            {
                "id": str(m["_id"]),
                "sender_id": str(m["sender_id"]),
                "sender_role": m["sender_role"],
                "content": m["content"],
                "created_at": m["created_at"],
            }
            for m in messages
        ]
    }), 200
