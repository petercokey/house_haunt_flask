from flask import Blueprint, jsonify, request, g
from datetime import datetime
 Wallet, Transaction, User, House
from app.utils.auth_helpers import jwt_required

bp = Blueprint("wallet", __name__, url_prefix="/api/wallet")


# 🟢 Health check
@bp.route("/ping")
def ping():
    return jsonify({"message": "wallet blueprint active"}), 200


# ==========================================================
# 🔹 View wallet balance
# ==========================================================
@bp.route("/balance", methods=["GET"])
@jwt_required()
def get_wallet_balance():
    user = g.user
    wallet = Wallet.query.filter_by(user_id=user.id).first()

    if not wallet:
        return jsonify({"balance": 0, "message": "Wallet not found"}), 404

    return jsonify({
        "user_id": user.id,
        "username": user.username,
        "balance": wallet.balance
    }), 200


# ==========================================================
# 🔹 Top up wallet
# ==========================================================
@bp.route("/topup", methods=["POST"])
@jwt_required()
def top_up_wallet():
    user = g.user
    data = request.get_json() or {}
    amount = data.get("amount")

    if not amount or amount <= 0:
        return jsonify({"error": "Invalid top-up amount"}), 400

    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0)
        db.session.add(wallet)

    wallet.balance += amount

    txn = Transaction(
        user_id=user.id,
        amount=amount,
        txn_type="credit",
        description=f"Wallet top-up of {amount}",
        created_at=datetime.utcnow(),
    )

    db.session.add(txn)
    db.session.commit()

    return jsonify({
        "message": f"Wallet topped up with {amount}",
        "new_balance": wallet.balance
    }), 200


# ==========================================================
# 🔹 View all approved houses (for haunters)
# ==========================================================
@bp.route("/houses", methods=["GET"])
@jwt_required()
def get_all_houses():
    """
    Return all approved houses available for haunters,
    with support for search, filtering, and sorting.
    """
    user = g.user
    if user.role != "haunter":
        return jsonify({"error": "Access denied. Only haunters allowed."}), 403

    query = House.query.filter_by(status="approved")

    # 🔍 Optional search and filters
    search = request.args.get("search", "").strip().lower()
    location = request.args.get("location", "").strip().lower()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    sort_by = request.args.get("sort_by", "newest")  # options: newest, price_asc, price_desc

    # 🔹 Apply filters
    if search:
        query = query.filter(
            db.or_(
                House.title.ilike(f"%{search}%"),
                House.description.ilike(f"%{search}%")
            )
        )
    if location:
        query = query.filter(House.location.ilike(f"%{location}%"))
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
