from flask import Blueprint, jsonify, request, g
from bson import ObjectId
from datetime import datetime
from app.extensions import mongo
from app.utils.auth_helpers import jwt_required
from app.utils.decorators import role_required
from app.utils.notify import create_notification

bp = Blueprint("contact", __name__, url_prefix="/api/contact")


@bp.route("/ping")
def ping():
    return jsonify({"message": "contact blueprint active"}), 200

# Haunter requests agent contact
@bp.route("/request/<string:agent_id>", methods=["POST"])
@jwt_required()
@role_required("haunter")
def request_contact(agent_id):
    """Allow haunter to request contact info from an agent using wallet credits."""
    agent = mongo.db.users.find_one({"_id": ObjectId(agent_id), "role": "agent"})
    if not agent:
        return jsonify({"error": "Invalid agent ID"}), 404

    wallet = mongo.db.wallets.find_one({"user_id": ObjectId(g.user["_id"])})
    if not wallet or wallet.get("balance", 0) < 2:
        return jsonify({"error": "Insufficient credits. Please top up."}), 402

    credits
