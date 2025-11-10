# app/routes/contact.py
from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
from datetime import datetime
 User, Wallet, ContactRequest, Notification, Transaction, House
from app.utils.decorators import role_required
from app.utils.notify import create_notification


bp = Blueprint("contact", __name__, url_prefix="/api/contact")


@bp.route("/ping")
def ping():
    return jsonify({"message": "contact blueprint active"}), 200


# 🔹 Haunter requests agent contact
@bp.route("/request/<int:agent_id>", methods=["POST"])
@login_required
@role_required("haunter")
def request_contact(agent_id):
    """Allow haunter to request contact info from an agent using wallet credits."""

    agent = User.query.get(agent_id)
    if not agent or agent.role != "agent":
        return jsonify({"error": "Invalid agent ID"}), 404

    # ✅ Wallet check
    wallet = Wallet.query.filter_by(user_id=current_user.id).first()
    if not wallet or wallet.balance < 2:
        return jsonify({"error": "Insufficient credits. Please top up."}), 402

    # ✅ Deduct 2 credits per contact request
    credits_used = 2
    wallet.balance -= credits_used

    # ✅ Log the transaction
    txn = Transaction(
        user_id=current_user.id,
        amount=-credits_used,
        txn_type="deduction",
        description=f"Requested contact info from {agent.username}",
        created_at=datetime.utcnow(),
    )
    db.session.add(txn)

    # ✅ Record the contact request
    contact_request = ContactRequest(
        haunter_id=current_user.id,
        agent_id=agent_id,
        created_at=datetime.utcnow(),
    )
    db.session.add(contact_request)

    # ✅ Commit DB changes before sending notifications
    db.session.commit()

    # ✅ Send notifications
    create_notification(current_user.id, f"{credits_used} credits deducted for contacting an agent.")
    create_notification(agent.id, f"A haunter ({current_user.username}) just requested your contact information.")

    return jsonify({
        "message": f"Contact request sent to {agent.username}",
        "remaining_balance": wallet.balance
    }), 201


# 🔹 Agent views incoming contact requests
@bp.route("/requests", methods=["GET"])
@login_required
@role_required("agent")
def get_contact_requests():
    """List all contact requests for the logged-in agent."""

    requests = ContactRequest.query.filter_by(agent_id=current_user.id).order_by(
        ContactRequest.created_at.desc()
    ).all()

    results = []
    for req in requests:
        haunter = User.query.get(req.haunter_id)
        results.append({
            "id": req.id,
            "haunter_name": haunter.username if haunter else "Unknown",
            "haunter_email": haunter.email if haunter else "N/A",
            "requested_at": req.created_at,
        })

    return jsonify({
        "total_requests": len(results),
        "requests": results
    }), 200
