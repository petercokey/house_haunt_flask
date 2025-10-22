from flask import Blueprint, jsonify, request
from flask_login import current_user
from app.models import (
    db,
    User,
    House,
    ContactRequest,
    Wallet,
    Notification,
    Transaction,
    Favorite
)
from app.utils.decorators import role_required
from datetime import datetime
from app.utils.notify import create_notification
from sqlalchemy import or_
from app.extensions import bcrypt
from app.utils.auth_helpers import jwt_or_login_required
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request

bp = Blueprint("haunter", __name__, url_prefix="/api/haunter")


# 🟢 Test route
@bp.route("/ping")
def ping():
    return jsonify({"message": "haunter blueprint active!"}), 200


# Helper: unified current user (works for JWT + Flask-Login)
def get_authenticated_user():
    """Return the authenticated user (JWT or Flask-Login)."""
    if current_user and not current_user.is_anonymous:
        return current_user
    try:
        verify_jwt_in_request()
        identity = get_jwt_identity()
        return User.query.get(identity["id"])
    except Exception:
        return None


# 🔹 Get all approved houses (with optional search & filters)
# ==========================================================
# 🔹 Get All Houses (Haunter Feed)
# ==========================================================
@bp.route("/houses", methods=["GET"])
@jwt_or_login_required(role="haunter")
def get_all_houses():
    """
    Fetch all approved houses to show in the haunter's feed.
    Includes image URLs and agent details.
    """
    try:
        from app.models import House, User

        houses = (
            db.session.query(House, User.username.label("agent_name"))
            .join(User, House.agent_id == User.id)
            .filter(House.status == "approved")
            .order_by(House.created_at.desc())
            .all()
        )

        result = []
        for house, agent_name in houses:
            result.append({
                "id": house.id,
                "title": house.title,
                "price": house.price,
                "location": house.location,
                "description": house.description,
                "image_url": house.image_url or (
                    f"https://househaunt.onrender.com/uploads/{house.image_path}"
                    if house.image_path else None
                ),
                "agent_name": agent_name,
                "created_at": house.created_at.isoformat(),
            })

        return jsonify({"houses": result}), 200

    except Exception as e:
        print("🔥 Error fetching houses:", e)
        return jsonify({"error": "Failed to fetch houses"}), 500


# 🔹 Get details of a specific house
@bp.route("/house/<int:house_id>", methods=["GET"])
@jwt_or_login_required(role="haunter")
def get_house_details(house_id):
    """Return detailed info of a specific approved house."""
    house = House.query.filter_by(id=house_id, status="approved").first()
    if not house:
        return jsonify({"error": "House not found or not approved yet."}), 404

    agent = User.query.get(house.agent_id)
    return jsonify({
        "id": house.id,
        "title": house.title,
        "description": house.description,
        "location": house.location,
        "price": house.price,
        "image_url": house.image_path,
        "agent": {
            "id": agent.id if agent else None,
            "name": agent.username if agent else "Unknown Agent",
            "email": agent.email if agent else None
        },
        "created_at": house.created_at
    }), 200


# 🔹 Haunter requests contact info (deducts credits)
@bp.route("/contact-agent/<int:house_id>", methods=["POST"])
@jwt_or_login_required(role="haunter")
def contact_agent(house_id):
    """Allow haunter to request an agent’s contact info using wallet credits."""
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    house = House.query.filter_by(id=house_id, status="approved").first()
    if not house:
        return jsonify({"error": "House not found or not approved."}), 404

    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if not wallet or wallet.balance < 2:
        return jsonify({"error": "Insufficient credits. Please top up."}), 402

    wallet.balance -= 2

    txn = Transaction(
        user_id=user.id,
        amount=-2,
        txn_type="deduction",
        description=f"Requested contact info for house '{house.title}'",
        created_at=datetime.utcnow(),
    )
    db.session.add(txn)

    contact_request = ContactRequest(
        haunter_id=user.id,
        agent_id=house.agent_id,
        house_id=house.id,
        created_at=datetime.utcnow(),
    )
    db.session.add(contact_request)

    create_notification(house.agent_id, f"A haunter just requested contact for your listing '{house.title}'.")
    create_notification(user.id, f"2 credits deducted for contacting the agent of '{house.title}'.")

    db.session.commit()

    return jsonify({
        "message": f"Contact request sent for '{house.title}'.",
        "remaining_balance": wallet.balance
    }), 201


# 🔹 Favorite / Unfavorite a house
@bp.route("/favorite/<int:house_id>", methods=["POST"])
@jwt_or_login_required(role="haunter")
def toggle_favorite(house_id):
    """Add or remove a house from haunter's favorites."""
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    house = House.query.get(house_id)
    if not house or house.status != "approved":
        return jsonify({"error": "House not found or not approved."}), 404

    favorite = Favorite.query.filter_by(haunter_id=user.id, house_id=house_id).first()

    if favorite:
        db.session.delete(favorite)
        db.session.commit()
        return jsonify({"message": f"Removed '{house.title}' from favorites."}), 200
    else:
        fav = Favorite(haunter_id=user.id, house_id=house_id, created_at=datetime.utcnow())
        db.session.add(fav)
        db.session.commit()
        return jsonify({"message": f"Added '{house.title}' to favorites."}), 201


# 🔹 View all favorites
@bp.route("/favorites", methods=["GET"])
@jwt_or_login_required(role="haunter")
def get_favorites():
    """Return all favorite houses of the logged-in haunter."""
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    favorites = Favorite.query.filter_by(haunter_id=user.id).all()
    results = []
    for f in favorites:
        house = House.query.get(f.house_id)
        if house and house.status == "approved":
            results.append({
                "id": house.id,
                "title": house.title,
                "location": house.location,
                "price": house.price,
                "image_url": house.image_path
            })
    return jsonify({
        "total_favorites": len(results),
        "favorites": results
    }), 200


# 🔹 Smart Recommendations System
@bp.route("/recommendations", methods=["GET"])
@jwt_or_login_required(role="haunter")
def get_recommendations():
    """Recommend houses based on the haunter’s favorites and contact history."""
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    favorite_house_ids = [f.house_id for f in Favorite.query.filter_by(haunter_id=user.id)]
    contacted_house_ids = [c.house_id for c in ContactRequest.query.filter_by(haunter_id=user.id)]

    interacted_ids = set(favorite_house_ids + contacted_house_ids)
    if not interacted_ids:
        return jsonify({"message": "No activity yet — explore houses to get personalized recommendations."}), 200

    reference_houses = House.query.filter(House.id.in_(interacted_ids)).all()
    recommended_query = House.query.filter(House.status == "approved", ~House.id.in_(interacted_ids))

    conditions = []
    for ref in reference_houses:
        conditions.append(
            db.and_(
                House.location.ilike(f"%{ref.location}%"),
                House.price.between(ref.price * 0.8, ref.price * 1.2)
            )
        )

    if conditions:
        recommended_query = recommended_query.filter(db.or_(*conditions))

    recommended_houses = recommended_query.order_by(House.created_at.desc()).limit(10).all()

    if not recommended_houses:
        return jsonify({"message": "No similar houses found at the moment."}), 200

    results = []
    for h in recommended_houses:
        agent = User.query.get(h.agent_id)
        results.append({
            "id": h.id,
            "title": h.title,
            "location": h.location,
            "price": h.price,
            "image_url": h.image_path,
            "agent": agent.username if agent else "Unknown Agent"
        })

    return jsonify({
        "total_recommendations": len(results),
        "recommendations": results
    }), 200


# 🔹 Trending Houses (Most Popular)
@bp.route("/trending", methods=["GET"])
@jwt_or_login_required(role="haunter")
def get_trending_houses():
    """Return top trending houses based on number of favorites and contact requests."""
    from sqlalchemy import func

    favorite_counts = (
        db.session.query(Favorite.house_id, func.count(Favorite.id).label("fav_count"))
        .group_by(Favorite.house_id)
        .subquery()
    )

    contact_counts = (
        db.session.query(ContactRequest.house_id, func.count(ContactRequest.id).label("req_count"))
        .group_by(ContactRequest.house_id)
        .subquery()
    )

    query = (
        db.session.query(
            House,
            (func.coalesce(favorite_counts.c.fav_count, 0) +
             func.coalesce(contact_counts.c.req_count, 0)).label("popularity")
        )
        .outerjoin(favorite_counts, House.id == favorite_counts.c.house_id)
        .outerjoin(contact_counts, House.id == contact_counts.c.house_id)
        .filter(House.status == "approved")
        .order_by(db.desc("popularity"), db.desc(House.created_at))
        .limit(10)
    )

    trending = query.all()

    if not trending:
        return jsonify({"message": "No trending houses yet."}), 200

    results = []
    for house, score in trending:
        agent = User.query.get(house.agent_id)
        results.append({
            "id": house.id,
            "title": house.title,
            "location": house.location,
            "price": house.price,
            "popularity_score": int(score),
            "image_url": house.image_path,
            "agent": {
                "id": agent.id if agent else None,
                "name": agent.username if agent else "Unknown Agent"
            },
        })

    return jsonify({
        "total_trending": len(results),
        "houses": results
    }), 200
