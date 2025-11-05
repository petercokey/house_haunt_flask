# app/routes/agent.py

from flask import Blueprint, jsonify, request, current_app, g
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from app.models import db, House, User, Transaction, ContactRequest, Notification, KYC
from app.utils.auth_helpers import jwt_required
from app.utils.decorators import role_required, admin_required
from app.extensions import bcrypt


bp = Blueprint("agent", __name__, url_prefix="/api/agent")


# 🟢 Test route
@bp.route("/ping")
def ping():
    return jsonify({"message": "agent blueprint active!"}), 200


# ✅ Allowed file types for house images
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename):
    """Check if uploaded file has allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# ==========================================================
# 🔹 AGENT HOUSE MANAGEMENT
# ==========================================================

# 🔹 Agent creates a new house listing
@bp.route("/create-house", methods=["POST"])
@jwt_required()
@role_required("agent")
def create_house():
    """Allow agents to create new house listings with image upload."""
    user = g.user

    title = request.form.get("title")
    description = request.form.get("description")
    location = request.form.get("location")
    price = request.form.get("price")

    if not all([title, description, location, price]):
        return jsonify({"error": "All fields (title, description, location, price) are required."}), 400

    # 🔹 Handle image upload
    if "image" not in request.files:
        return jsonify({"error": "House image is required."}), 400

    file = request.files["image"]
    if file.filename == "":
        return jsonify({"error": "No selected file."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid image type. Allowed: png, jpg, jpeg, webp"}), 400

    # Create upload folder if not exists
    folder = os.path.join(current_app.root_path, "uploads", "house_images")
    os.makedirs(folder, exist_ok=True)

    # Save image with safe filename
    filename = secure_filename(f"{user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    image_path = os.path.join(folder, filename)
    file.save(image_path)

    # ✅ Save house record in DB
    house = House(
        agent_id=user.id,
        title=title,
        description=description,
        location=location,
        price=float(price),
        image_path=image_path,
        created_at=datetime.utcnow(),
        status="pending"
    )

    db.session.add(house)
    db.session.commit()

    return jsonify({
        "message": "House created successfully!",
        "house": {
            "id": house.id,
            "title": house.title,
            "location": house.location,
            "price": house.price,
            "image_url": f"/uploads/house_images/{filename}"
        }
    }), 201


# 🔹 Get all houses by logged-in agent
@bp.route("/my-houses", methods=["GET"])
@jwt_required()
@role_required("agent")
def my_houses():
    """Return all houses created by the logged-in agent."""
    user = g.user
    houses = House.query.filter_by(agent_id=user.id).order_by(House.created_at.desc()).all()

    results = [{
        "id": h.id,
        "title": h.title,
        "description": h.description,
        "location": h.location,
        "price": h.price,
        "image_url": h.image_path,
        "status": getattr(h, "status", "pending"),
        "created_at": h.created_at
    } for h in houses]

    return jsonify({
        "total_houses": len(results),
        "houses": results
    }), 200


# 🔹 Edit an existing house listing
@bp.route("/edit-house/<int:house_id>", methods=["PUT"])
@jwt_required()
@role_required("agent")
def edit_house(house_id):
    """Allow agents to edit their own house listing."""
    user = g.user
    house = House.query.filter_by(id=house_id, agent_id=user.id).first()

    if not house:
        return jsonify({"error": "House not found or unauthorized."}), 404

    title = request.form.get("title", house.title)
    description = request.form.get("description", house.description)
    location = request.form.get("location", house.location)
    price = request.form.get("price", house.price)

    house.title = title
    house.description = description
    house.location = location
    house.price = float(price)

    # Optional new image upload
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename:
            if not allowed_file(file.filename):
                return jsonify({"error": "Invalid image type."}), 400

            folder = os.path.join(current_app.root_path, "uploads", "house_images")
            os.makedirs(folder, exist_ok=True)
            filename = secure_filename(f"{user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            image_path = os.path.join(folder, filename)
            file.save(image_path)
            house.image_path = image_path

    db.session.commit()

    return jsonify({
        "message": "House updated successfully!",
        "house": {
            "id": house.id,
            "title": house.title,
            "location": house.location,
            "price": house.price,
            "image_url": house.image_path
        }
    }), 200


# 🔹 Delete a house
@bp.route("/delete-house/<int:house_id>", methods=["DELETE"])
@jwt_required()
@role_required("agent")
def delete_house(house_id):
    """Allow agents to delete their own house listing."""
    user = g.user
    house = House.query.filter_by(id=house_id, agent_id=user.id).first()

    if not house:
        return jsonify({"error": "House not found or unauthorized."}), 404

    db.session.delete(house)
    db.session.commit()

    return jsonify({"message": f"House '{house.title}' deleted successfully."}), 200


# ==========================================================
# 🔹 ADMIN HOUSE MANAGEMENT
# ==========================================================

@bp.route("/all-houses", methods=["GET"])
@jwt_required()
@admin_required
def all_houses():
    """Admin view of all house listings."""
    houses = House.query.order_by(House.created_at.desc()).all()
    results = []

    for h in houses:
        agent = User.query.get(h.agent_id)
        results.append({
            "id": h.id,
            "title": h.title,
            "description": h.description,
            "location": h.location,
            "price": h.price,
            "status": getattr(h, "status", "active"),
            "agent": {
                "id": agent.id if agent else None,
                "name": agent.username if agent else "Deleted User",
                "email": agent.email if agent else "N/A"
            },
            "image_url": h.image_path,
            "created_at": h.created_at
        })

    return jsonify({
        "total_houses": len(results),
        "houses": results
    }), 200


@bp.route("/review-house/<int:house_id>", methods=["POST"])
@jwt_required()
@admin_required
def review_house(house_id):
    """Admin can approve or reject a house listing."""
    data = request.get_json()
    decision = data.get("decision")
    note = data.get("note", "")

    if decision not in ["approved", "rejected"]:
        return jsonify({"error": "Decision must be 'approved' or 'rejected'"}), 400

    house = House.query.get(house_id)
    if not house:
        return jsonify({"error": "House not found"}), 404

    house.status = decision
    db.session.commit()

    msg = f"Your house '{house.title}' has been {decision.upper()}. {note}"
    notification = Notification(user_id=house.agent_id, message=msg)
    db.session.add(notification)
    db.session.commit()

    return jsonify({
        "message": f"House '{house.title}' {decision} successfully.",
        "note": note
    }), 200


@bp.route("/delete-house-admin/<int:house_id>", methods=["DELETE"])
@jwt_required()
@admin_required
def delete_house_admin(house_id):
    """Allow admin to delete any house listing."""
    house = House.query.get(house_id)
    if not house:
        return jsonify({"error": "House not found"}), 404

    db.session.delete(house)
    db.session.commit()

    msg = f"Your house '{house.title}' has been removed by the admin."
    notification = Notification(user_id=house.agent_id, message=msg)
    db.session.add(notification)
    db.session.commit()

    return jsonify({"message": f"House '{house.title}' deleted by admin."}), 200


# ==========================================================
# 🔹 AGENT PROFILE & DASHBOARD
# ==========================================================

@bp.route("/profile", methods=["GET"])
@jwt_required()
@role_required("agent")
def get_agent_profile():
    user = g.user
    kyc_record = KYC.query.filter_by(agent_id=user.id).first()

    return jsonify({
        "id": user.id,
        "username": user.username,
        "email": user.email,
        "role": user.role,
        "credits": user.credits,
        "kyc_verified": user.kyc_verified,
        "kyc_status": kyc_record.status if kyc_record else "not_submitted",
        "created_at": user.created_at
    }), 200


@bp.route("/profile/update", methods=["PUT"])
@jwt_required()
@role_required("agent")
def update_agent_profile():
    user = g.user
    data = request.get_json()
    username = data.get("username")
    email = data.get("email")

    if not username or not email:
        return jsonify({"error": "Username and email are required"}), 400

    user.username = username
    user.email = email
    db.session.commit()

    return jsonify({"message": "Profile updated successfully!"}), 200


@bp.route("/profile/change-password", methods=["PUT"])
@jwt_required()
@role_required("agent")
def change_password():
    user = g.user
    data = request.get_json()
    old_password = data.get("old_password")
    new_password = data.get("new_password")

    if not old_password or not new_password:
        return jsonify({"error": "Both old and new passwords are required"}), 400

    if not bcrypt.check_password_hash(user.password, old_password):
        return jsonify({"error": "Old password is incorrect"}), 401

    user.password = bcrypt.generate_password_hash(new_password).decode("utf-8")
    db.session.commit()

    return jsonify({"message": "Password updated successfully!"}), 200


# ==========================================================
# 🔹 AGENT DASHBOARD SUMMARY & NOTIFICATIONS
# ==========================================================

@bp.route("/summary", methods=["GET"])
@jwt_required()
@role_required("agent")
def agent_summary():
    user = g.user

    total_posts = House.query.filter_by(agent_id=user.id).count()
    total_contacts = ContactRequest.query.filter_by(agent_id=user.id).count()
    total_transactions = Transaction.query.filter_by(user_id=user.id).count()

    kyc = KYC.query.filter_by(agent_id=user.id).first()
    kyc_status = kyc.status if kyc else "not_submitted"

    summary = {
        "username": user.username,
        "email": user.email,
        "credits": user.credits,
        "total_posts": total_posts,
        "total_contacts": total_contacts,
        "total_transactions": total_transactions,
        "kyc_status": kyc_status,
    }

    return jsonify(summary), 200


@bp.route("/notifications", methods=["GET"])
@jwt_required()
@role_required("agent")
def get_agent_notifications():
    user = g.user
    notifications = (
        Notification.query
        .filter_by(user_id=user.id)
        .order_by(Notification.created_at.desc())
        .limit(20)
        .all()
    )

    results = [
        {
            "id": n.id,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        }
        for n in notifications
    ]

    return jsonify({"total": len(results), "notifications": results}), 200