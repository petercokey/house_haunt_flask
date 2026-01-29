# app/routes/admin.py
from flask import Blueprint, jsonify, request
from bson import ObjectId
from datetime import datetime
from app.extensions import mongo
from app.utils.auth_helpers import jwt_required, admin_required

bp = Blueprint("admin", __name__, url_prefix="/api/admin")


# ============================================================
# HELPERS
# ============================================================

def serialize_user(user):
    if not user:
        return None
    return {
        "id": str(user["_id"]),
        "username": user.get("username"),
        "email": user.get("email"),
        "role": user.get("role"),
        "created_at": user.get("created_at"),
    }


# ============================================================
# ADMIN DASHBOARD (OVERVIEW)
# ============================================================

@bp.route("/dashboard", methods=["GET"])
@jwt_required()
@admin_required
def admin_dashboard():
    users = list(mongo.db.users.find({}))
    houses = list(mongo.db.houses.find({}))
    reviews = list(mongo.db.reviews.find({}))
    kycs = list(mongo.db.kyc.find({}))
    contact_requests = list(mongo.db.contact_requests.find({}))

    agents = [u for u in users if u.get("role") == "agent"]
    haunters = [u for u in users if u.get("role") == "haunter"]

    avg_rating = (
        round(sum(r.get("rating", 0) for r in reviews) / len(reviews), 2)
        if reviews else 0
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
# GET ALL HOUSES
# ============================================================

@bp.route("/houses", methods=["GET"])
@jwt_required()
@admin_required
def get_all_houses():
    houses = list(mongo.db.houses.find({}))
    agents = {
        a["_id"]: a
        for a in mongo.db.users.find({"role": "agent"})
    }

    results = []
    for h in houses:
        agent = agents.get(h.get("agent_id"))
        images = h.get("images", [])

        results.append({
            "id": str(h["_id"]),
            "title": h.get("title"),
            "description": h.get("description"),
            "location": h.get("location"),
            "price": h.get("price"),
            "images": images,
            "preview_image": images[0] if images else None,
            "status": h.get("status"),
            "agent": serialize_user(agent),
            "created_at": h.get("created_at"),
        })

    return jsonify({
        "total": len(results),
        "houses": results
    }), 200


# ============================================================
# APPROVE / REJECT HOUSE
# ============================================================

@bp.route("/review-house/<house_id>", methods=["POST"])
@jwt_required()
@admin_required
def review_house(house_id):
    data = request.get_json() or {}
    decision = data.get("decision")

    if decision not in ("approved", "rejected"):
        return jsonify({"error": "decision must be approved or rejected"}), 400

    house = mongo.db.houses.find_one({"_id": ObjectId(house_id)})
    if not house:
        return jsonify({"error": "House not found"}), 404

    mongo.db.houses.update_one(
        {"_id": ObjectId(house_id)},
        {"$set": {
            "status": decision,
            "reviewed_at": datetime.utcnow(),
        }}
    )

    return jsonify({
        "message": f"House '{house.get('title')}' has been {decision}"
    }), 200


# ============================================================
# GET ALL KYC RECORDS
# ============================================================

@bp.route("/kyc", methods=["GET"])
@jwt_required()
@admin_required
def get_all_kyc():
    kycs = list(mongo.db.kyc.find().sort("uploaded_at", -1))
    users = {
        u["_id"]: u
        for u in mongo.db.users.find({"role": "agent"})
    }

    results = []
    for k in kycs:
        agent = users.get(k["agent_id"])

        results.append({
            "id": str(k["_id"]),
            "agent": serialize_user(agent),
            "full_name": k.get("full_name"),
            "id_type": k.get("id_type"),
            "documents": k.get("id_documents", []),
            "status": k.get("status"),
            "uploaded_at": k.get("uploaded_at"),
            "reviewed_at": k.get("reviewed_at"),
            "admin_note": k.get("admin_note"),
        })

    return jsonify({
        "total": len(results),
        "kyc_records": results
    }), 200


# ============================================================
# GET ALL CONTACT REQUESTS
# ============================================================

@bp.route("/contact-requests", methods=["GET"])
@jwt_required()
@admin_required
def get_contact_requests():
    requests = list(mongo.db.contact_requests.find({}))
    users = {
        u["_id"]: u
        for u in mongo.db.users.find({})
    }

    results = []
    for r in requests:
        haunter = users.get(r.get("haunter_id"))
        agent = users.get(r.get("agent_id"))

        results.append({
            "id": str(r["_id"]),
            "house_id": str(r.get("house_id")),
            "status": r.get("status"),
            "haunter": serialize_user(haunter),
            "agent": serialize_user(agent),
            "created_at": r.get("created_at"),
        })

    return jsonify({
        "total": len(results),
        "requests": results
    }), 200


# ============================================================
# GET ALL USERS BY ROLE
# ============================================================

@bp.route("/users/<role>", methods=["GET"])
@jwt_required()
@admin_required
def get_users_by_role(role):
    if role not in ("agent", "haunter", "admin"):
        return jsonify({"error": "Invalid role"}), 400

    users = list(mongo.db.users.find({"role": role}))

    return jsonify({
        "total": len(users),
        "users": [serialize_user(u) for u in users]
    }), 200