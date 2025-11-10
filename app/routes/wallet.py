from flask import Blueprint, jsonify, request, g
from datetime import datetime
from bson import ObjectId
from app import mongo
from app.utils.auth_helpers import jwt_required

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
    data = request.get_json() or {}
    amount = data.get("amount")

    if not amount or amount <= 0:
        return jsonify({"error": "Invalid top-up amount"}), 400

    wallet = mongo.db.wallets.find_one({"user_id": user_id})
    if wallet:
        new_balance = wallet.get("balance", 0) + amount
        mongo.db.wallets.update_one({"_id": wallet["_id"]}, {"$set": {"balance": new_balance}})
    else:
        new_balance = amount
        mongo.db.wallets.insert_one({"user_id": user_id, "balance": new_balance})

    mongo.db.transactions.insert_one({
        "user_id": user_id,
        "amount": amount,
        "txn_type": "credit",
        "description": f"Wallet top-up of {amount}",
        "created_at": datetime.utcnow()
    })

    return jsonify({
        "message": f"Wallet topped up with {amount}",
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
