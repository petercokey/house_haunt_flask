print("ADMIN ROUTES LOADED FROM:", __file__)
# app/routes/admin.py
from flask import Blueprint, jsonify, request
from bson import ObjectId
from datetime import datetime
from app import mongo
from app.utils.auth_helpers import jwt_required, admin_required

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

# ============================================================
# ADMIN DASHBOARD (Overview)
# ============================================================
@bp.route("/dashboard", methods=["GET"])
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

    avg_rating = (
        round(sum(r.get("rating", 0) for r in reviews) / len(reviews), 2)
        if reviews
        else 0
    )

    return jsonify({
        "summary": {
            "total_users": len(users),
            "total_agents": len(agents),
            "total_haunters": len(haunters),
        },
        "kyc": {
            "total": len(kycs),
            "pending": sum(1 for k in kycs if k.get("status") == "pending"),
            "approved": sum(1 for k in kycs if k.get("status") == "approved"),
            "rejected": sum(1 for k in kycs if k.get("status") == "rejected"),
        },
        "properties": {
            "total": len(houses),
            "pending": sum(1 for h in houses if h.get("status") == "pending"),
            "approved": sum(1 for h in houses if h.get("status") == "approved"),
            "rejected": sum(1 for h in houses if h.get("status") == "rejected"),
        },
        "reviews": {
            "total": len(reviews),
            "average_rating": avg_rating,
        },
        "contact_requests": len(contact_requests),
    }), 200


# ============================================================
# GET ALL PENDING HOUSES
# ============================================================
@bp.route("/pending-houses", methods=["GET"])
# @jwt_required()
# @admin_required
def get_pending_houses():
    return {"ok": True}

# ============================================================
# GET ALL HOUSES
# ============================================================
@bp.route("/all-houses", methods=["GET"])
@jwt_required()
@admin_required
def get_all_houses():
    houses = list(mongo.db.houses.find({}))
    results = []

    for h in houses:
        agent = mongo.db.users.find_one({"_id": h.get("agent_id")})

        results.append({
            "id": str(h["_id"]),
            "title": h.get("title"),
            "description": h.get("description"),
            "location": h.get("location"),
            "price": h.get("price"),
            "image_url": h.get("image_path"),
            "status": h.get("status"),
            "agent": {
                "id": str(agent["_id"]) if agent else None,
                "name": agent.get("username") if agent else "Unknown",
            },
            "created_at": h.get("created_at"),
        })

    return jsonify({"total": len(results), "houses": results}), 200


# ============================================================
# APPROVE / REJECT HOUSE
# ============================================================
@bp.route("/review-house/<house_id>", methods=["POST"])
@jwt_required()
@admin_required
def review_house(house_id):
    data = request.get_json()
    decision = data.get("decision")

    if decision not in ("approved", "rejected"):
        return jsonify({"error": "decision must be approved or rejected"}), 400

    house = mongo.db.houses.find_one({"_id": ObjectId(house_id)})
    if not house:
        return jsonify({"error": "House not found"}), 404

    mongo.db.houses.update_one(
        {"_id": ObjectId(house_id)},
        {
            "$set": {
                "status": decision,
                "reviewed_at": datetime.utcnow(),
            }
        },
    )

    return jsonify({
        "message": f"House '{house.get('title')}' has been {decision}"
    }), 200
