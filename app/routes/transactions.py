from flask import Blueprint, jsonify, g
 Transaction
from app.utils.auth_helpers import jwt_required

bp = Blueprint("transactions", __name__, url_prefix="/api/transactions")


# ðŸŸ¢ Health check
@bp.route("/ping")
def ping():
    return jsonify({"message": "Transactions blueprint active!"}), 200


# ==========================================================
# ðŸ”¹ View all transactions for the logged-in user
# ==========================================================
@bp.route("/", methods=["GET"])
@jwt_required()
def get_transactions():
    """Return all wallet transactions for the authenticated user."""
    user = g.user
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    transactions = (
        Transaction.query
        .filter_by(user_id=user.id)
        .order_by(Transaction.created_at.desc())
        .all()
    )

    results = [
        {
            "id": t.id,
            "amount": t.amount,
            "txn_type": t.txn_type,
            "description": t.description,
            "created_at": t.created_at,
        }
        for t in transactions
    ]

    total_credits_used = sum(t.amount for t in transactions if t.amount < 0)
    total_credits_earned = sum(t.amount for t in transactions if t.amount > 0)

    return jsonify({
        "total_transactions": len(results),
        "credits_spent": abs(total_credits_used),
        "credits_earned": total_credits_earned,
        "transactions": results
    }), 200


# ==========================================================
# ðŸ”¹ Delete all transaction history
# ==========================================================
@bp.route("/clear", methods=["DELETE"])
@jwt_required()
def clear_transactions():
    """Delete all wallet transactions for the authenticated user."""
    user = g.user
    if not user:
        return jsonify({"error": "Unauthorized"}), 401

    deleted = Transaction.query.filter_by(user_id=user.id).delete()
    db.session.commit()

    return jsonify({"message": f"{deleted} transactions cleared."}), 200
