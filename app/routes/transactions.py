# app/routes/transactions.py
from flask import Blueprint, jsonify, g
from datetime import datetime
from bson import ObjectId
from app.extensions import mongo
from app.utils.auth_helpers import jwt_required

bp = Blueprint("transactions", __name__, url_prefix="/api/transactions")

@bp.route("/ping")
def ping():
    return jsonify({"message": "Transactions blueprint active!"}), 200


# View all transactions for logged-in user
@bp.route("/", methods=["GET"])
@jwt_required()
def get_transactions():
    user_id = g.user["_id"]
    transactions = list(mongo.db.transactions.find({"user_id": user_id}).sort("created_at", -1))

    results = [{
        "id": str(t["_id"]),
        "amount": t["amount"],
        "txn_type": t["txn_type"],
        "description": t.get("description"),
        "created_at": t.get("created_at")
    } for t in transactions]

    total_credits_used = sum(t["amount"] for t in transactions if t["amount"] < 0)
    total_credits_earned = sum(t["amount"] for t in transactions if t["amount"] > 0)

    return jsonify({
        "total_transactions": len(results),
        "credits_spent": abs(total_credits_used),
        "credits_earned": total_credits_earned,
        "transactions": results
    }), 200


# Clear all transaction history
@bp.route("/clear", methods=["DELETE"])
@jwt_required()
def clear_transactions():
    user_id = g.user["_id"]
    result = mongo.db.transactions.delete_many({"user_id": user_id})
    return jsonify({"message": f"{result.deleted_count} transactions cleared."}), 200
