from flask import Blueprint, jsonify, request, g
from app.utils.notify import create_notification
from app.utils.auth_helpers import jwt_required, role_required
from app.extensions import mongo
from bson import ObjectId
from datetime import datetime

from app.models import (
    Review,
    ContactRequest,
    User
)

bp = Blueprint("review", __name__, url_prefix="/api/review")

@bp.route("/ping")
def ping():
    return jsonify({"message": "Review blueprint active!"}), 200


# Haunter posts a review for an agent
@bp.route("", methods=["POST"])
@jwt_required()
@role_required("haunter")
def create_review():
    data = request.get_json()

    agent_id = data.get("agent_id")
    rating = data.get("rating")
    comment = data.get("comment", "")

    if not agent_id or not rating:
        return jsonify({"error": "agent_id and rating required"}), 400

    try:
        agent_obj = ObjectId(agent_id)
    except:
        return jsonify({"error": "Invalid agent id"}), 400

    existing = mongo.db.reviews.find_one({
        "agent_id": agent_obj,
        "reviewer_id": g.user["_id"]
    })

    if existing:
        return jsonify({"error": "You already reviewed this agent"}), 400

    mongo.db.reviews.insert_one({
        "agent_id": agent_obj,
        "reviewer_id": g.user["_id"],
        "rating": rating,
        "comment": comment,
        "created_at": datetime.utcnow()
    })

    return jsonify({"message": "Review submitted"}), 201