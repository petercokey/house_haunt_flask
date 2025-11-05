from flask import Blueprint, jsonify, request
from datetime import datetime
from app.models import db, Wallet, Transaction, User, House
from app.utils.auth_helpers import jwt_required

bp = Blueprint("wallet", __name__, url_prefix="/api/wallet")


# ==========================================================
# 🟢 Health check
# ==========================================================
@bp.route("/ping")
def ping():
    return jsonify({"message": "wallet blueprint active"}), 200


# ==========================================================
# 🔹 Get wallet balance
# ==========================================================
@bp.route("/", methods=["GET"])
@jwt_required()
def get_wallet_balance():
    """Return the current user's wallet balance and transactions."""
    from flask_jwt_extended import get_jwt_identity

    identity = get_jwt_identity()
    user = User.query.get(identity["id"])

    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0)
        db.session.add(wallet)
        db.session.commit()

    transactions = Transaction.query.filter_by(user_id=user.id).order_by(Transaction.created_at.desc()).all()

    txn_list = [
        {
            "id": t.id,
            "amount": t.amount,
            "txn_type": t.txn_type,
            "description": t.description,
            "created_at": t.created_at,
        }
        for t in transactions
    ]

    return jsonify({
        "balance": wallet.balance,
        "total_transactions": len(txn_list),
        "transactions": txn_list
    }), 200


# ==========================================================
# 🔹 Top up wallet
# ==========================================================
@bp.route("/topup", methods=["POST"])
@jwt_required()
def top_up_wallet():
    """Add credits to the user's wallet."""
    from flask_jwt_extended import get_jwt_identity

    identity = get_jwt_identity()
    user = User.query.get(identity["id"])

    data = request.get_json()
    amount = data.get("amount", 0)

    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if not wallet:
        wallet = Wallet(user_id=user.id, balance=0)
        db.session.add(wallet)

    wallet.balance += amount

    txn = Transaction(
        user_id=user.id,
        amount=amount,
        txn_type="topup",
        description=f"Topped up {amount} credits.",
        created_at=datetime.utcnow()
    )
    db.session.add(txn)
    db.session.commit()

    return jsonify({
        "message": f"{amount} credits added successfully.",
        "new_balance": wallet.balance
    }), 200


# ==========================================================
# 🔹 Spend credits
# ==========================================================
@bp.route("/spend", methods=["POST"])
@jwt_required()
def spend_credits():
    """Deduct credits from the wallet for an action."""
    from flask_jwt_extended import get_jwt_identity

    identity = get_jwt_identity()
    user = User.query.get(identity["id"])

    data = request.get_json()
    amount = data.get("amount", 0)
    description = data.get("description", "Wallet deduction")

    if amount <= 0:
        return jsonify({"error": "Invalid amount"}), 400

    wallet = Wallet.query.filter_by(user_id=user.id).first()
    if not wallet or wallet.balance < amount:
        return jsonify({"error": "Insufficient credits"}), 402

    wallet.balance -= amount

    txn = Transaction(
        user_id=user.id,
        amount=-amount,
        txn_type="deduction",
        description=description,
        created_at=datetime.utcnow()
    )
    db.session.add(txn)
    db.session.commit()

    return jsonify({
        "message": f"{amount} credits deducted successfully.",
        "remaining_balance": wallet.balance
    }), 200


# ==========================================================
# 🔹 View all approved houses (for haunters)
# ==========================================================
@bp.route("/houses", methods=["GET"])
@jwt_required(role="haunter")
def get_all_houses():
    """Return all approved houses available for haunters."""
    from flask_jwt_extended import get_jwt_identity

    identity = get_jwt_identity()
    user = User.query.get(identity["id"])

    query = House.query.filter_by(status="approved")

    # 🔍 Optional search and filters
    search = request.args.get("search", "").strip().lower()
    location = request.args.get("location", "").strip().lower()
    min_price = request.args.get("min_price", type=float)
    max_price = request.args.get("max_price", type=float)
    sort_by = request.args.get("sort_by", "newest")

    # 🔹 Apply search and filters
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
