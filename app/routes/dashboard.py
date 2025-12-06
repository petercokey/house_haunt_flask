from flask import Blueprint, jsonify, g
from bson import ObjectId
from app import mongo
from app.utils.auth_helpers import jwt_required
from app.utils.decorators import role_required, admin_required

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.route("/ping")
def ping():
    return jsonify({"message": "dashboard blueprint active!"}), 200


# -------------------------
# Agent Dashboard
# -------------------------


def convert_objectid(obj):
    """Recursively convert all ObjectIds in dict/list to strings."""
    if isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj

@bp.route("/agent", methods=["GET"])
@jwt_required()
@role_required("agent")
def agent_dashboard():
    user_id = g.user["_id"]

    # Fetch data from MongoDB
    kyc = mongo.db.kyc.find_one({"agent_id": user_id})
    wallet = mongo.db.wallets.find_one({"user_id": user_id})
    houses = list(mongo.db.houses.find({"agent_id": user_id}))
    reviews = list(mongo.db.reviews.find({"agent_id": user_id}))
    contact_requests = list(mongo.db.contact_requests.find({"agent_id": user_id}))

    # Compute average rating safely
    avg_rating = round(sum(r.get("rating", 0) for r in reviews) / len(reviews), 2) if reviews else 0

    # Prepare data for JSON response
    response = {
        "agent": {
            "id": str(user_id),
            "name": g.user.get("username", ""),
            "email": g.user.get("email", ""),
            "joined_on": g.user.get("created_at")
        },
        "wallet": {
            "balance": wallet.get("balance", 0) if wallet else 0,
            "credits_spent": wallet.get("credits_spent", 0) if wallet else 0
        },
        "kyc": {
            "status": kyc.get("status", "not_submitted") if kyc else "not_submitted",
            "uploaded_at": kyc.get("uploaded_at") if kyc else None,
            "reviewed_at": kyc.get("reviewed_at") if kyc else None
        },
        "houses": houses,
        "reviews": reviews,
        "average_rating": avg_rating,
        "contact_requests": contact_requests
    }

    # Convert all ObjectIds to strings recursively
    response_safe = convert_objectid(response)

    return jsonify(response_safe), 200



# -------------------------
# Haunter Dashboard
# -------------------------
@bp.route("/haunter", methods=["GET"])
@jwt_required()
@role_required("haunter")
def haunter_dashboard():
    user_id = g.user["_id"]

    wallet = mongo.db.wallets.find_one({"user_id": user_id})
    requests = list(mongo.db.contact_requests.find({"haunter_id": user_id}))
    reviews = list(mongo.db.reviews.find({"haunter_id": user_id}))

    requested_houses = []
    for r in requests:
        house = mongo.db.houses.find_one({"_id": r.get("house_id")})
        if house:
            requested_houses.append({
                "id": str(house["_id"]),
                "title": house["title"],
                "location": house["location"],
                "price": house["price"],
                "agent_id": str(house["agent_id"])
            })

    return jsonify({
        "haunter": {
            "id": str(user_id),
            "name": g.user.get("username"),
            "email": g.user.get("email"),
            "joined_on": g.user.get("created_at")
        },
        "wallet": {
            "balance": wallet.get("balance", 0) if wallet else 0,
            "last_updated": wallet.get("updated_at") if wallet else None
        },
        "requested_houses": requested_houses,
        "reviews_written": [{
            "agent_id": str(r["agent_id"]),
            "rating": r["rating"],
            "comment": r.get("comment", "")
        } for r in reviews],
        "total_requests": len(requested_houses),
        "total_reviews": len(reviews)
    }), 200


# -------------------------
# Admin Dashboard
# -------------------------
@bp.route("/admin", methods=["GET"])
@jwt_required()
@admin_required
def admin_dashboard():
    users = list(mongo.db.users.find({}))
    agents = [u for u in users if u.get("role") == "agent"]
    haunters = [u for u in users if u.get("role") == "haunter"]

    kycs = list(mongo.db.kyc.find({}))
    houses = list(mongo.db.houses.find({}))
    reviews = list(mongo.db.reviews.find({}))
    contact_requests = list(mongo.db.contact_requests.find({}))

    avg_rating = round(sum(r.get("rating", 0) for r in reviews) / len(reviews), 2) if reviews else 0

    top_agents = {}
    for r in reviews:
        agent_id = str(r["agent_id"])
        top_agents.setdefault(agent_id, []).append(r["rating"])

    top_agents_sorted = sorted(
        [{"agent": agent_id, "avg_rating": round(sum(rs)/len(rs), 2)} for agent_id, rs in top_agents.items()],
        key=lambda x: x["avg_rating"], reverse=True
    )[:5]

    return jsonify({
        "summary": {
            "users": len(users),
            "agents": len(agents),
            "haunters": len(haunters)
        },
        "kyc": {
            "total": len(kycs),
            "pending": sum(1 for k in kycs if k.get("status") == "pending"),
            "approved": sum(1 for k in kycs if k.get("status") == "approved"),
            "rejected": sum(1 for k in kycs if k.get("status") == "rejected")
        },
        "properties": len(houses),
        "reviews": {
            "total": len(reviews),
            "average_rating": avg_rating
        },
        "contact_requests": len(contact_requests),
        "top_agents": top_agents_sorted
    }), 200
