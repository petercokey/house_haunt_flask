from flask import Blueprint, jsonify, request, g
from bson import ObjectId
from datetime import datetime
from app import mongo
from app.utils.auth_helpers import jwt_required
from app.utils.decorators import role_required

bp = Blueprint("haunter_chat", __name__, url_prefix="/api/haunter/chat")

@bp.route("/chats", methods=["GET"])
@jwt_required()
@role_required("haunter")
def get_haunter_chats():
    chats = list(
        mongo.db.chats.find({"haunter_id": g.user["_id"]})
        .sort("created_at", -1)
    )

    return jsonify({
        "chats": [
            {
                "chat_id": str(c["_id"]),
                "agent_id": str(c["agent_id"]),
                "created_at": c["created_at"]
            }
            for c in chats
        ]
    }), 200


@bp.route("/chats/<chat_id>/messages", methods=["POST"])
@jwt_required()
@role_required("haunter")
def send_message(chat_id):
    content = (request.get_json() or {}).get("content")
    if not content:
        return jsonify({"error": "Message required"}), 400

    chat = mongo.db.chats.find_one({
        "_id": ObjectId(chat_id),
        "haunter_id": g.user["_id"],
    })

    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    mongo.db.messages.insert_one({
        "chat_id": ObjectId(chat_id),
        "sender_id": g.user["_id"],
        "sender_role": "haunter",
        "content": content,
        "created_at": datetime.utcnow(),
    })

    return jsonify({"message": "Sent"}), 201
