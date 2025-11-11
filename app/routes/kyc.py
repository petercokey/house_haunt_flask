import os
from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from datetime import datetime
from app.utils.decorators import role_required, admin_required
from app.utils.email_utils import send_email
from app.utils.notify import create_notification
from app.utils.auth_helpers import jwt_required


from app.models import (
    KYC,
    User,
    Notification
)

bp = Blueprint("kyc", __name__, url_prefix="/api/kyc")

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "..", "uploads", "kyc_docs")
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/ping")
def ping():
    return jsonify({"message": "KYC blueprint active!"}), 200


# Upload KYC (agent)
@bp.route("/upload", methods=["POST"])
@jwt_required()
@role_required("agent")
def upload_kyc_file():
    user_id = g.user["_id"]
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]
    if file.filename == "" or not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type"}), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    filename = secure_filename(f"{user_id}_{file.filename}")
    file_path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(file_path)

    existing = mongo.db.kyc.find_one({"agent_id": user_id})
    if existing:
        mongo.db.kyc.update_one({"_id": existing["_id"]}, {"$set": {
            "file_path": file_path,
            "status": "pending",
            "uploaded_at": datetime.utcnow()
        }})
    else:
        mongo.db.kyc.insert_one({
            "agent_id": user_id,
            "file_path": file_path,
            "status": "pending",
            "uploaded_at": datetime.utcnow()
        })

    return jsonify({"message": "KYC uploaded successfully!"}), 201


# KYC Status
@bp.route("/status", methods=["GET"])
@jwt_required()
@role_required("agent")
def get_kyc_status():
    user_id = g.user["_id"]
    record = mongo.db.kyc.find_one({"agent_id": user_id})
    if not record:
        return jsonify({"status": "not_submitted"}), 200

    return jsonify({
        "status": record.get("status"),
        "uploaded_at": record.get("uploaded_at"),
        "reviewed_at": record.get("reviewed_at"),
        "admin_note": record.get("admin_note")
    }), 200


# Admin: view all KYC
@bp.route("/all", methods=["GET"])
@jwt_required()
@role_required("admin")
def view_all_kyc():
    kycs = list(mongo.db.kyc.find().sort("uploaded_at", -1))
    data = [{
        "id": str(k["_id"]),
        "agent_id": str(k["agent_id"]),
        "status": k.get("status"),
        "uploaded_at": k.get("uploaded_at"),
        "reviewed_at": k.get("reviewed_at"),
        "admin_note": k.get("admin_note"),
        "file_path": k.get("file_path")
    } for k in kycs]
    return jsonify({"kyc_records": data}), 200


# Admin: approve/reject KYC
@bp.route("/review/<agent_id>", methods=["POST"])
@jwt_required()
@role_required("admin")
def review_kyc(agent_id):
    data = request.get_json()
    decision = data.get("decision")
    note = data.get("note", "")

    record = mongo.db.kyc.find_one({"agent_id": ObjectId(agent_id)})
    if not record:
        return jsonify({"error": "No KYC found for this agent"}), 404
    if decision not in ["approved", "rejected"]:
        return jsonify({"error": "Invalid decision"}), 400

    mongo.db.kyc.update_one({"_id": record["_id"]}, {"$set": {
        "status": decision,
        "admin_note": note,
        "reviewed_at": datetime.utcnow()
    }})

    create_notification(ObjectId(agent_id), f"KYC {decision.upper()} — {note or 'No comment'}")

    agent = mongo.db.users.find_one({"_id": ObjectId(agent_id)})
    if agent and agent.get("email"):
        send_email(
            f"KYC {decision.capitalize()}",
            [agent["email"]],
            f"Hello {agent['username']}, your KYC has been {decision.upper()}.\n\nNote: {note or 'No comment.'}"
        )

    return jsonify({"message": f"KYC {decision} successfully"}), 200


# Serve KYC document
@bp.route("/view/<kyc_id>", methods=["GET"])
@jwt_required()
def view_kyc_document(kyc_id):
    record = mongo.db.kyc.find_one({"_id": ObjectId(kyc_id)})
    if not record:
        return jsonify({"error": "KYC not found"}), 404

    if record["agent_id"] != g.user["_id"] and g.user.get("role") != "admin":
        return jsonify({"error": "Unauthorized"}), 403

    if not os.path.exists(record["file_path"]):
        return jsonify({"error": "File not found"}), 404

    folder, filename = os.path.split(record["file_path"])
    return send_from_directory(folder, filename)
