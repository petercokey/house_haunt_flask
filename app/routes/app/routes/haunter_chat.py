from flask import Blueprint, jsonify, request, g
from datetime import datetime
from bson import ObjectId
from app import mongo
from app.utils.auth_helpers import jwt_required
from app.utils.decorators import role_required

bp = Blueprint("haunter_chat", __name__, url_prefix="/api/haunter/chats")

@bp.route("/", methods=["GET"])
@jwt_required()
@role_required("haunter")
def get_haunter_chats():
    haunter_id = g.user["_id"]

    chats = list(
        mongo.db.chats.find({"haunter_id": haunter_id})
        .sort("created_at", -1)
    )

    results = []

    for chat in chats:
        agent = mongo.db.users.find_one(
            {"_id": chat["agent_id"]},
            {"username": 1, "email": 1}
        )

        results.append({
            "chat_id": str(chat["_id"]),
            "created_at": chat["created_at"],
            "agent": {
                "id": str(agent["_id"]) if agent else None,
                "username": agent.get("username") if agent else "Unknown",
                "email": agent.get("email") if agent else None,
            }
        })

    return jsonify({
        "total": len(results),
        "chats": results
    }), 200

@bp.route("/<chat_id>/messages", methods=["GET"])
@jwt_required()
@role_required("haunter")
def get_chat_messages(chat_id):
    haunter_id = g.user["_id"]

    chat = mongo.db.chats.find_one({
        "_id": ObjectId(chat_id),
        "haunter_id": haunter_id,
    })

    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    messages = list(
        mongo.db.messages
        .find({"chat_id": ObjectId(chat_id)})
        .sort("created_at", 1)
    )

    return jsonify({
        "messages": [
            {
                "id": str(m["_id"]),
                "sender_role": m["sender_role"],
                "content": m["content"],
                "created_at": m["created_at"]
            }
            for m in messages
        ]
    }), 200

@bp.route("/<chat_id>/messages", methods=["POST"])
@jwt_required()
@role_required("haunter")
def send_message(chat_id):
    haunter_id = g.user["_id"]
    data = request.get_json() or {}
    content = data.get("content")

    if not content:
        return jsonify({"error": "Message content required"}), 400

    chat = mongo.db.chats.find_one({
        "_id": ObjectId(chat_id),
        "haunter_id": haunter_id,
    })

    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    mongo.db.messages.insert_one({
        "chat_id": ObjectId(chat_id),
        "sender_id": haunter_id,
        "sender_role": "haunter",
        "content": content,
        "created_at": datetime.utcnow(),
    })

    return jsonify({"message": "Message sent"}), 201
