from flask import Blueprint, jsonify
from flask_login import login_required, current_user
from app.models import User, Wallet, Review, ContactRequest, KYC, House
from app import db
from app.utils.decorators import role_required, admin_required


bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")

# 🟢 Test route
@bp.route("/ping")
def ping():
    return jsonify({"message": "dashboard blueprint active!"}), 200


# 🔹 Agent Dashboard
@bp.route("/agent", methods=["GET"])
@login_required
@role_required("agent")
def agent_dashboard():
    """Return all agent dashboard data: KYC, houses, reviews, wallet, and contact requests."""

    agent_info = {
        "id": current_user.id,
        "name": current_user.username,
        "email": current_user.email,
        "joined_on": getattr(current_user, "created_at", None)
    }

    # KYC Info
    kyc = KYC.query.filter_by(agent_id=current_user.id).first()
    kyc_info = {
        "status": kyc.status if kyc else "not_submitted",
        "uploaded_at": getattr(kyc, "uploaded_at", None),
        "reviewed_at": getattr(kyc, "reviewed_at", None),
    }

    # Wallet Info
    wallet = Wallet.query.filter_by(user_id=current_user.id).first()
    wallet_info = {
        "balance": getattr(wallet, "balance", 0),
        "credits_spent": getattr(wallet, "credits_spent", 0)
    }

    # Houses Listed
    houses = House.query.filter_by(agent_id=current_user.id).all()
    houses_list = [
        {"id": h.id, "title": h.title, "price": h.price, "location": h.location}
        for h in houses
    ]

    # Reviews
    reviews = Review.query.filter_by(agent_id=current_user.id).all()
    reviews_list = [
        {"rating": r.rating, "comment": r.comment, "haunter_id": r.haunter_id}
        for r in reviews
    ]
    avg_rating = round(sum(r.rating for r in reviews) / len(reviews), 2) if reviews else 0

    # Contact Requests
    requests = ContactRequest.query.filter_by(agent_id=current_user.id).all()
    contact_requests = []
    for req in requests:
        haunter = User.query.get(req.haunter_id)
        house = House.query.get(req.house_id)
        contact_requests.append({
            "request_id": req.id,
            "haunter": {
                "id": haunter.id if haunter else None,
                "name": haunter.username if haunter else "Unknown",
                "email": haunter.email if haunter else "N/A"
            },
            "house": {
                "id": house.id if house else None,
                "title": house.title if house else "Deleted Listing"
            },
            "requested_at": getattr(req, "created_at", None)
        })

    return jsonify({
        "agent": agent_info,
        "wallet": wallet_info,
        "kyc": kyc_info,
        "houses": houses_list,
        "reviews": reviews_list,
        "average_rating": avg_rating,
        "contact_requests": contact_requests
    }), 200


# 🔹 Haunter Dashboard
@bp.route("/haunter", methods=["GET"])
@login_required
@role_required("haunter")
def haunter_dashboard():
    """Return all dashboard data for the logged-in haunter"""

    haunter_info = {
        "id": current_user.id,
        "name": current_user.username,
        "email": current_user.email,
        "joined_on": getattr(current_user, "created_at", None)
    }

    # Wallet details
    wallet = Wallet.query.filter_by(user_id=current_user.id).first()
    wallet_info = {
        "balance": wallet.balance if wallet else 0,
        "last_updated": getattr(wallet, "updated_at", None)
    }

    # Houses they requested contact for
    requests = ContactRequest.query.filter_by(haunter_id=current_user.id).all()
    requested_houses = []
    for r in requests:
        house = House.query.get(r.house_id)
        if house:
            requested_houses.append({
                "id": house.id,
                "title": house.title,
                "location": house.location,
                "price": house.price,
                "agent_id": house.agent_id,
            })

    # Reviews written by this haunter
    reviews = Review.query.filter_by(haunter_id=current_user.id).all()
    review_list = [
        {"agent_id": r.agent_id, "rating": r.rating, "comment": r.comment}
        for r in reviews
    ]

    return jsonify({
        "haunter": haunter_info,
        "wallet": wallet_info,
        "requested_houses": requested_houses,
        "reviews_written": review_list,
        "total_requests": len(requested_houses),
        "total_reviews": len(reviews)
    }), 200


# 🔹 Admin Dashboard
@bp.route("/admin", methods=["GET"])
@login_required
@admin_required
def admin_dashboard():
    """Admin view: global summary of agents, haunters, KYC, and system stats."""

    total_users = User.query.count()
    total_agents = User.query.filter_by(role="agent").count()
    total_haunters = User.query.filter_by(role="haunter").count()

    total_kyc = KYC.query.count()
    pending_kyc = KYC.query.filter_by(status="pending").count()
    approved_kyc = KYC.query.filter_by(status="approved").count()
    rejected_kyc = KYC.query.filter_by(status="rejected").count()

    total_houses = House.query.count()
    total_reviews = Review.query.count()
    avg_rating = round(sum(r.rating for r in Review.query.all()) / total_reviews, 2) if total_reviews else 0
    total_requests = ContactRequest.query.count()

    top_agents = (
        db.session.query(User.username, db.func.avg(Review.rating).label("avg_rating"))
        .join(Review, Review.agent_id == User.id)
        .filter(User.role == "agent")
        .group_by(User.username)
        .order_by(db.desc("avg_rating"))
        .limit(5)
        .all()
    )
    top_agents_list = [{"agent": a[0], "avg_rating": float(a[1])} for a in top_agents]

    return jsonify({
        "summary": {
            "users": total_users,
            "agents": total_agents,
            "haunters": total_haunters,
        },
        "kyc": {
            "total": total_kyc,
            "pending": pending_kyc,
            "approved": approved_kyc,
            "rejected": rejected_kyc
        },
        "properties": total_houses,
        "reviews": {
            "total": total_reviews,
            "average_rating": avg_rating
        },
        "contact_requests": total_requests,
        "top_agents": top_agents_list
    }), 200
