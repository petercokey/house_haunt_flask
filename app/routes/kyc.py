import os
from flask import Blueprint, jsonify, request, current_app, g, send_from_directory
from werkzeug.utils import secure_filename
from datetime import datetime
from app.utils.auth_helpers import jwt_required, role_required, admin_required
from app.utils.email_utils import send_email
from app.utils.notify import create_notification
from app.extensions import mongo
from bson import ObjectId

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
def upload_kyc():
    agent_id = g.user["_id"]

    full_name = request.form.get("full_name")
    id_type = request.form.get("id_type")
    files = request.files.getlist("id_documents")

    if not full_name or not id_type:
        return jsonify({"error": "full_name and id_type are required"}), 400

    if not files or len(files) == 0:
        return jsonify({"error": "ID document is required"}), 400

    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    saved_files = []

    for file in files:
        if file.filename == "" or not allowed_file(file.filename):
            continue

        filename = secure_filename(f"{agent_id}_{datetime.utcnow().timestamp()}_{file.filename}")
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        saved_files.append(file_path)

    if not saved_files:
        return jsonify({"error": "No valid documents uploaded"}), 400

    mongo.db.kyc.update_one(
        {"agent_id": agent_id},
        {"$set": {
            "full_name": full_name,
            "id_type": id_type,
            "id_documents": saved_files,
            "status": "pending",
            "uploaded_at": datetime.utcnow()
        }},
        upsert=True
    )

    return jsonify({"message": "KYC submitted successfully"}), 201


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
# Admin: view all KYC
@bp.route("/all", methods=["GET"])
@jwt_required()
@role_required("admin")
def view_all_kyc():
    kycs = list(mongo.db.kyc.find().sort("uploaded_at", -1))

    data = []
    for k in kycs:
        data.append({
            "id": str(k["_id"]),
            "agent_id": str(k["agent_id"]),
            "status": k.get("status"),
            "uploaded_at": k.get("uploaded_at"),
            "reviewed_at": k.get("reviewed_at"),
            "admin_note": k.get("admin_note"),
            "documents": k.get("id_documents", [])  # ✅ Correct field
        })

    return jsonify({"kyc_records": data}), 200

