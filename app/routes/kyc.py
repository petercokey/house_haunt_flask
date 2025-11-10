import os
from flask import Blueprint, jsonify, request, current_app
from flask_login import current_user, login_required
from werkzeug.utils import secure_filename
from datetime import datetime
from app.utils.decorators import role_required, admin_required
 KYC, User, Notification
from app.utils.email_utils import send_email
from app.utils.notify import create_notification


bp = Blueprint("kyc", __name__, url_prefix="/api/kyc")

# 🟢 Test route
@bp.route("/ping")
def ping():
    return jsonify({"message": "KYC blueprint active!"}), 200


# 🔹 Allowed file extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "pdf"}

def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# 🔹 Agent uploads ID document (file)
@bp.route("/upload", methods=["POST"])
@login_required
def upload_kyc_file():
    if current_user.role != "agent":
        return jsonify({"error": "Only agents can upload KYC."}), 403

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded."}), 400

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid file type. Allowed: png, jpg, jpeg, pdf"}), 400

    # Create upload folder if not exists
    folder = os.path.join(current_app.root_path, "uploads", "kyc_docs")
    os.makedirs(folder, exist_ok=True)

    filename = secure_filename(f"{current_user.id}_{file.filename}")
    path = os.path.join(folder, filename)
    file.save(path)

    # Save record to DB
    record = KYC(
        agent_id=current_user.id,
        file_path=path,
        status="pending",
        uploaded_at=datetime.utcnow(),
    )
    db.session.add(record)
    db.session.commit()

    return jsonify({"message": "KYC uploaded successfully!"}), 201


# 🔹 Agent checks their KYC status
@bp.route("/status", methods=["GET"])
@login_required
def get_kyc_status():
    if current_user.role != "agent":
        return jsonify({"error": "Only agents can view KYC status."}), 403

    record = KYC.query.filter_by(agent_id=current_user.id).first()
    if not record:
        return jsonify({"status": "not_submitted"}), 200

    return jsonify({
        "status": record.status,
        "uploaded_at": record.uploaded_at,
        "reviewed_at": record.reviewed_at,
        "admin_note": record.admin_note
    }), 200


# 🔹 Admin: view all KYC submissions
@bp.route("/all", methods=["GET"])
@login_required
@admin_required
def view_all_kyc():
    kycs = KYC.query.order_by(KYC.uploaded_at.desc()).all()
    data = [
        {
            "id": k.id,
            "agent_id": k.agent_id,
            "status": k.status,
            "uploaded_at": k.uploaded_at,
            "reviewed_at": k.reviewed_at,
            "admin_note": k.admin_note,
            "file_path": k.file_path
        }
        for k in kycs
    ]
    return jsonify({"kyc_records": data}), 200


# 🔹 Admin: approve or reject a KYC
@bp.route("/review/<int:agent_id>", methods=["POST"])
@login_required
@admin_required
def review_kyc(agent_id):
    data = request.get_json()
    decision = data.get("decision")  # "approved" or "rejected"
    note = data.get("note", "")

    record = KYC.query.filter_by(agent_id=agent_id).first()
    if not record:
        return jsonify({"error": "No KYC found for this agent"}), 404

    record.status = decision
    record.admin_note = note
    record.reviewed_at = datetime.utcnow()

    # ✅ Notify agent
    note_msg = f"KYC {decision.upper()} - {note or 'No comment'}"
    notify = Notification(user_id=agent_id, message=note_msg)
    db.session.add(notify)
    db.session.commit()
    create_notification(agent_id, f"Your KYC has been {decision.upper()} — {note or 'No comment'}")


    # ✅ Optional email notification
    agent = User.query.get(agent_id)
    if agent and agent.email:
        body = (
            f"Hello {agent.username},\n\n"
            f"Your KYC submission has been {decision.upper()}.\n\n"
            f"Admin note: {note if note else 'No additional comment.'}\n\n"
            "Thank you for using HouseHaunt!"
        )
        send_email(f"KYC {decision.capitalize()}", [agent.email], body)

    return jsonify({"message": f"KYC {decision} successfully"}), 200


