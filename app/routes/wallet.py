# app/routes/wallet.py
from flask import Blueprint, jsonify, request, g
from datetime import datetime
from app.extensions import mongo
from app.utils.auth_helpers import jwt_required

from app.models import (
    Wallet,
    Transaction,
    User,
    House
)

bp = Blueprint("wallet", __name__, url_prefix="/api/wallet")


@bp.route("/ping")
def ping():
    return jsonify({"message": "Wallet blueprint active"}), 200

# View wallet balance
@bp.route("/balance", methods=["GET"])
@jwt_required()
def get_wallet_balance():
    user_id = g.user["_id"]
    wallet = mongo.db.wallets.find_one({"user_id": user_id})

    if not wallet:
        return jsonify({"balance": 0, "message": "Wallet not found"}), 404

    return jsonify({
        "user_id": str(user_id),
        "username": g.user["username"],
        "balance": wallet.get("balance", 0)
    }), 200

# Top up wallet
@bp.route("/topup", methods=["POST"])
@jwt_required()
def top_up_wallet():
    user_id = g.user["_id"]

    # Accept both JSON and form-data (for frontend flexibility)
    data = request.get_json(silent=True) or request.form
    input_amount = data.get("amount")  # optional, for logging

    # Free mode: give a large balance regardless of input
    free_amount = 100000  # arbitrary large amount for testing

    # Fetch existing wallet or create new one
    wallet = mongo.db.wallets.find_one({"user_id": user_id})
    if wallet:
        new_balance = wallet.get("balance", 0) + free_amount
        mongo.db.wallets.update_one(
            {"_id": wallet["_id"]}, 
            {"$set": {"balance": new_balance, "updated_at": datetime.utcnow()}}
        )
    else:
        new_balance = free_amount
        mongo.db.wallets.insert_one({
            "user_id": user_id,
            "balance": new_balance,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow()
        })

    # Record transaction for logging purposes
    mongo.db.transactions.insert_one({
        "user_id": user_id,
        "amount": free_amount,
        "txn_type": "credit",
        "description": f"Free top-up (input was {input_amount})",
        "created_at": datetime.utcnow()
    })

    return jsonify({
        "message": f"Wallet topped up with {free_amount} (free mode)",
        "new_balance": new_balance
    }), 200



# View all approved houses (for haunters)
@bp.route("/houses", methods=["GET"])
@jwt_required()
def get_all_houses():
    if g.user.get("role") != "haunter":
        return jsonify({"error": "Access denied. Only haunters allowed."}), 403

    query = {"status": "approved"}
    houses = list(mongo.db.houses.find(query).sort("created_at", -1))

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
            "agent": {
                "id": str(agent["_id"]) if agent else None,
                "name": agent["username"] if agent else "Unknown Agent"
            },
            "created_at": h.get("created_at")
        })

    return jsonify({
        "total_results": len(results),
        "houses": results
    }), 200
