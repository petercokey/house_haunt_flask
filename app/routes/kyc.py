import os
from flask import Blueprint, jsonify, request, g, redirect
from datetime import datetime
from bson import ObjectId
import cloudinary
import cloudinary.uploader

from app.utils.auth_helpers import jwt_required, role_required
from app.extensions import mongo

bp = Blueprint("kyc", __name__, url_prefix="/api/kyc")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}


# ----------------------------
# Cloudinary Config
# ----------------------------
cloudinary.config(
    cloud_name=os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key=os.getenv("CLOUDINARY_API_KEY"),
    api_secret=os.getenv("CLOUDINARY_API_SECRET"),
    secure=True
)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/ping")
def ping():
    return jsonify({"message": "KYC blueprint active!"}), 200


# -------------------------------------------------
# Upload KYC (Agent → Cloudinary → Mongo)
# -------------------------------------------------
@bp.route("/upload", methods=["POST"])
@jwt_required()
@role_required("agent")
def upload_kyc():

    agent_id = str(g.user["_id"])
    full_name = request.form.get("full_name")
    id_type = request.form.get("id_type")
    files = request.files.getlist("id_documents")

    if not full_name or not id_type:
        return jsonify({"error": "full_name and id_type are required"}), 400

    if not files:
        return jsonify({"error": "ID document is required"}), 400

    uploaded_files = []

    for file in files:
        if file.filename == "" or not allowed_file(file.filename):
            continue

        try:
            result = cloudinary.uploader.upload(
                file,
                folder="kyc_docs",
                public_id=f"{agent_id}_{int(datetime.utcnow().timestamp())}",
                resource_type="auto"
            )

            uploaded_files.append({
                "url": result["secure_url"],
                "public_id": result["public_id"]
            })

        except Exception as e:
            return jsonify({"error": f"Cloudinary upload failed: {str(e)}"}), 500

    if not uploaded_files:
        return jsonify({"error": "No valid documents uploaded"}), 400

    mongo.db.kyc.update_one(
        {"agent_id": ObjectId(agent_id)},
        {"$set": {
            "full_name": full_name,
            "id_type": id_type,
            "id_documents": uploaded_files,
            "status": "pending",
            "uploaded_at": datetime.utcnow()
        }},
        upsert=True
    )

    return jsonify({"message": "KYC submitted successfully"}), 201


# -------------------------------------------------
# Agent: Check KYC Status
# -------------------------------------------------
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


# -------------------------------------------------
# Admin: View All KYC Records
# -------------------------------------------------
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
            "documents": k.get("id_documents", [])
        })

    return jsonify({"kyc_records": data}), 200


# -------------------------------------------------
# Admin: View Single KYC Document (Redirect)
# -------------------------------------------------
@bp.route("/view/<kyc_id>", methods=["GET"])
@jwt_required()
@role_required("admin")
def view_kyc_document(kyc_id):

    record = mongo.db.kyc.find_one({"_id": ObjectId(kyc_id)})
    if not record:
        return jsonify({"error": "KYC not found"}), 404

    documents = record.get("id_documents", [])
    if not documents:
        return jsonify({"error": "No document found"}), 404

    first_doc = documents[0]

    # 🔥 Handle BOTH formats (string and dict)
    if isinstance(first_doc, str):
        return redirect(first_doc)

    if isinstance(first_doc, dict):
        return redirect(first_doc.get("url"))

    return jsonify({"error": "Invalid document format"}), 500
