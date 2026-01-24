from flask import Blueprint, jsonify, request, g
from app.utils.decorators import role_required
from app.utils.notify import create_notification
from app.utils.auth_helpers import jwt_required  # ✅ add this
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
@bp.route("/add/<agent_id>", methods=["POST"])
@jwt_required()
@role_required("haunter")
def add_review(agent_id):
    user_id = g.user["_id"]
    agent = mongo.db.users.find_one({"_id": ObjectId(agent_id), "role": "agent"})
    if not agent:
        return jsonify({"error": "Invalid agent ID"}), 404

    data = request.get_json() or {}
    rating = data.get("rating")
    comment = (data.get("comment") or "").strip()

    if not rating or not (1 <= rating <= 5):
        return jsonify({"error": "Rating must be between 1 and 5"}), 400

    existing = mongo.db.reviews.find_one({"haunter_id": user_id, "agent_id": ObjectId(agent_id)})
    if existing:
        return jsonify({"error": "You have already reviewed this agent."}), 400

    mongo.db.reviews.insert_one({
        "haunter_id": user_id,
        "agent_id": ObjectId(agent_id),
        "rating": rating,
        "comment": comment,
        "created_at": datetime.utcnow()
    })

    message = f"You received a new review from {g.user['username']}: {rating}⭐ - '{comment or 'No comment'}'"
    create_notification(ObjectId(agent_id), message)

    return jsonify({"message": "Review posted successfully"}), 201


# Agent views all reviews they’ve received
@bp.route("/my", methods=["GET"])
@jwt_required()
@role_required("agent")
def my_reviews():
    agent_id = g.user["_id"]
    reviews = list(mongo.db.reviews.find({"agent_id": agent_id}).sort("created_at", -1))

    result = []
    for r in reviews:
        haunter = mongo.db.users.find_one({"_id": r["haunter_id"]})
        result.append({
            "haunter_id": str(r["haunter_id"]),
            "haunter_name": haunter["username"] if haunter else "Deleted User",
            "rating": r["rating"],
            "comment": r.get("comment", ""),
            "created_at": r.get("created_at")
        })

    avg_rating = round(sum(r["rating"] for r in result) / len(result), 2) if result else 0

    return jsonify({"total_reviews": len(result), "average_rating": avg_rating, "reviews": result}), 200
