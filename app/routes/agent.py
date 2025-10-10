import os
from flask import Blueprint, jsonify, request, current_app
from flask_login import login_required, current_user
from werkzeug.utils import secure_filename
from datetime import datetime
from app.models import db, House, User, Notification  # ✅ Added User + Notification
from app.utils.decorators import role_required, admin_required  # ✅ Combined imports

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


# 🔹 Agent creates a new house listing
@bp.route("/create-house", methods=["POST"])
@login_required
@role_required("agent")
def create_house():
    """Allow agents to create new house listings with image upload."""

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

    # Save image with a safe filename
    filename = secure_filename(f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
    image_path = os.path.join(folder, filename)
    file.save(image_path)

    # ✅ Save house record in DB
    house = House(
        agent_id=current_user.id,
        title=title,
        description=description,
        location=location,
        price=float(price),
        image_path=image_path,
        created_at=datetime.utcnow(),
        status="pending"  # ✅ newly added for moderation
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
@login_required
@role_required("agent")
def my_houses():
    """Return all houses created by the logged-in agent."""
    houses = House.query.filter_by(agent_id=current_user.id).order_by(House.created_at.desc()).all()

    results = []
    for h in houses:
        results.append({
            "id": h.id,
            "title": h.title,
            "description": h.description,
            "location": h.location,
            "price": h.price,
            "image_url": h.image_path,
            "status": getattr(h, "status", "pending"),
            "created_at": h.created_at
        })

    return jsonify({
        "total_houses": len(results),
        "houses": results
    }), 200


# 🔹 Edit an existing house listing
@bp.route("/edit-house/<int:house_id>", methods=["PUT"])
@login_required
@role_required("agent")
def edit_house(house_id):
    """Allow agents to edit their own house listing."""
    house = House.query.filter_by(id=house_id, agent_id=current_user.id).first()

    if not house:
        return jsonify({"error": "House not found or unauthorized."}), 404

    title = request.form.get("title", house.title)
    description = request.form.get("description", house.description)
    location = request.form.get("location", house.location)
    price = request.form.get("price", house.price)

    # ✅ Update optional fields
    house.title = title
    house.description = description
    house.location = location
    house.price = float(price)

    # ✅ Handle optional new image upload
    if "image" in request.files:
        file = request.files["image"]
        if file and file.filename:
            if not allowed_file(file.filename):
                return jsonify({"error": "Invalid image type."}), 400

            folder = os.path.join(current_app.root_path, "uploads", "house_images")
            os.makedirs(folder, exist_ok=True)
            filename = secure_filename(f"{current_user.id}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
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
@login_required
@role_required("agent")
def delete_house(house_id):
    """Allow agents to delete their own house listing."""
    house = House.query.filter_by(id=house_id, agent_id=current_user.id).first()

    if not house:
        return jsonify({"error": "House not found or unauthorized."}), 404

    db.session.delete(house)
    db.session.commit()

    return jsonify({"message": f"House '{house.title}' deleted successfully."}), 200


# ==========================================================
# 🔹 ADMIN HOUSE MANAGEMENT
# ==========================================================

# 🏠 Get all house listings (for admin)
@bp.route("/all-houses", methods=["GET"])
@login_required
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


# ✅ Approve or Reject House
@bp.route("/review-house/<int:house_id>", methods=["POST"])
@login_required
@admin_required
def review_house(house_id):
    """Admin can approve or reject a house listing."""
    data = request.get_json()
    decision = data.get("decision")  # "approved" or "rejected"
    note = data.get("note", "")

    if decision not in ["approved", "rejected"]:
        return jsonify({"error": "Decision must be 'approved' or 'rejected'"}), 400

    house = House.query.get(house_id)
    if not house:
        return jsonify({"error": "House not found"}), 404

    house.status = decision
    db.session.commit()

    # 🔔 Notify the agent
    msg = f"Your house '{house.title}' has been {decision.upper()}. {note}"
    notification = Notification(user_id=house.agent_id, message=msg)
    db.session.add(notification)
    db.session.commit()

    return jsonify({
        "message": f"House '{house.title}' {decision} successfully.",
        "note": note
    }), 200


# 🗑️ Delete a house listing (admin override)
@bp.route("/delete-house-admin/<int:house_id>", methods=["DELETE"])
@login_required
@admin_required
def delete_house_admin(house_id):
    """Allow admin to delete any house listing."""
    house = House.query.get(house_id)

    if not house:
        return jsonify({"error": "House not found"}), 404

    db.session.delete(house)
    db.session.commit()

    # 🔔 Notify the agent
    msg = f"Your house '{house.title}' has been removed by the admin."
    notification = Notification(user_id=house.agent_id, message=msg)
    db.session.add(notification)
    db.session.commit()

    return jsonify({"message": f"House '{house.title}' deleted by admin."}), 200
