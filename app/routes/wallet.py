from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
from app.models import db, Wallet, Transaction, Notification
from app.utils.decorators import role_required
from app.utils.notify import create_notification


bp = Blueprint("wallet", __name__, url_prefix="/api/wallet")


@bp.route("/ping")
def ping():
    return jsonify({"message": "wallet blueprint active"}), 200


# 🔹 View wallet balance
@bp.route("/balance", methods=["GET"])
@login_required
def view_balance():
    wallet = Wallet.query.filter_by(user_id=current_user.id).first()
    if not wallet:
        return jsonify({"balance": 0, "message": "Wallet not found"}), 200

    return jsonify({
        "user_id": current_user.id,
        "balance": wallet.balance,
        "credits_spent": wallet.credits_spent,
        "updated_at": wallet.updated_at
    }), 200


# 🔹 Top-up wallet
@bp.route("/topup", methods=["POST"])
@login_required
@role_required("haunter")
def topup_wallet():
    """Haunter adds credits to their wallet."""
    data = request.get_json()
    amount = data.get("amount", 0)

    if amount <= 0:
        return jsonify({"error": "Invalid top-up amount"}), 400

    wallet = Wallet.query.filter_by(user_id=current_user.id).first()
    if not wallet:
        wallet = Wallet(user_id=current_user.id, balance=0, credits_spent=0)
        db.session.add(wallet)

    wallet.balance += amount
    wallet.updated_at = datetime.utcnow()

    # Log transaction
    txn = Transaction(
        user_id=current_user.id,
        amount=amount,
        txn_type="topup",
        description="Wallet top-up",
        created_at=datetime.utcnow()
    )
    db.session.add(txn)
    db.session.commit()

    # ✅ Notify user of successful top-up
    create_notification(current_user.id, f"Your wallet was topped up with {amount} credits!")

    return jsonify({
        "message": f"Wallet topped up successfully with {amount} credits.",
        "new_balance": wallet.balance
    }), 200


# 🔹 Admin credit or debit adjustment
@bp.route("/adjust/<int:user_id>", methods=["POST"])
@login_required
@role_required("admin")
def adjust_wallet(user_id):
    """Admin can adjust wallet balance (credit or debit)."""
    data = request.get_json()
    amount = data.get("amount")
    reason = data.get("reason", "Admin adjustment")

    if amount == 0:
        return jsonify({"error": "Amount cannot be zero"}), 400

    wallet = Wallet.query.filter_by(user_id=user_id).first()
    if not wallet:
        wallet = Wallet(user_id=user_id, balance=0, credits_spent=0)
        db.session.add(wallet)

    wallet.balance += amount
    wallet.updated_at = datetime.utcnow()

    txn = Transaction(
        user_id=user_id,
        amount=amount,
        txn_type="admin_adjustment",
        description=reason,
        created_at=datetime.utcnow()
    )
    db.session.add(txn)
    db.session.commit()

    # ✅ Notify the affected user
    if amount > 0:
        msg = f"Your wallet has been credited with {amount} credits by admin. Reason: {reason}."
    else:
        msg = f"{abs(amount)} credits were deducted from your wallet by admin. Reason: {reason}."
    create_notification(user_id, msg)

    return jsonify({"message": "Wallet adjusted successfully"}), 200


