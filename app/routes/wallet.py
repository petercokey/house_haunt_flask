from flask import Blueprint, jsonify, request
from datetime import datetime
from app.models import db, Wallet, Transaction, User, House
from app.utils.auth_helpers import jwt_or_login_required, get_authenticated_user

bp = Blueprint("wallet", __name__, url_prefix="/api/wallet")


# 🟢 Health check
@bp.route("/ping")
def ping():
    return jsonify({"message": "wallet blueprint active"}), 200


# ==========================================================
# 🔹 View all approved houses (for haunters)
# ==========================================================
@bp.route("/houses", methods=["GET"])
@jwt_or_login_required(role="haunter")
def get_all_houses():
    """
    Return all approved houses available for haunters,
    with support for search, filtering, and sorting.
    """
    user = get_authenticated_user()
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    query = House.query.filter_by(status="approved")

    # 🔍 Optional search and filters
    search = request.args.get("search", "").strip().lower()
    location = request.args.get("location", "").strip().lower()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    sort_by = request.args.get("sort_by", "newest")  # options: newest, price_asc, price_desc

    # 🔹 Apply text search
    if search:
        query = query.filter(
            db.or_(
                House.title.ilike(f"%{search}%"),
                House.description.ilike(f"%{search}%")
            )
        )

    # 🔹 Filter by location
    if location:
        query = query.filter(House.location.ilike(f"%{location}%"))

    # 🔹 Filter by price range
    if min_price is not None:
        query = query.filter(House.price >= min_price)
    if max_price is not None:
        query = query.filter(House.price <= max_price)

    # 🔹 Sorting
    if sort_by == "price_asc":
        query = query.order_by(House.price.asc())
    elif sort_by == "price_desc":
        query = query.order_by(House.price.desc())
    else:
        query = query.order_by(House.created_at.desc())

    # 🔹 Execute query
    houses = query.all()

    results = []
    for h in houses:
        agent = User.query.get(h.agent_id)
        results.append({
            "id": h.id,
            "title": h.title,
            "description": h.description,
            "location": h.location,
            "price": h.price,
            "image_url": h.image_path,
            "agent": {
                "id": agent.id if agent else None,
                "name": agent.username if agent else "Unknown Agent"
            },
            "created_at": h.created_at
        })

    return jsonify({
        "total_results": len(results),
        "filters": {
            "search": search,
            "location": location,
            "min_price": min_price,
            "max_price": max_price,
            "sort_by": sort_by
        },
        "houses": results
    }), 200
