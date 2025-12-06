from flask import Blueprint, jsonify, request, current_app, g
from werkzeug.utils import secure_filename
from datetime import datetime
import os
from app.extensions import bcrypt
from app.utils.auth_helpers import jwt_required
from app.utils.decorators import role_required, admin_required
from bson import ObjectId

from app.models import (
    House,
    User,
    Transaction,
    ContactRequest,
    Notification,
    KYC
)


bp = Blueprint("agent", __name__, url_prefix="/api/agent")


# Allowed image extensions
ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


# -----------------------------
# Helper functions / Mongo Models
# -----------------------------
class House:
    @staticmethod
    def create(data):
        return current_app.mongo.db.houses.insert_one(data)

    @staticmethod
    def update_status(house_id, status):
        return current_app.mongo.db.houses.update_one(
            {"_id": ObjectId(house_id)}, {"$set": {"status": status}}
        )

    @staticmethod
    def find_by_agent(agent_id):
        return list(current_app.mongo.db.houses.find({"agent_id": str(agent_id)}))

    @staticmethod
    def find_all():
        return list(current_app.mongo.db.houses.find())


class User:
    @staticmethod
    def find_by_id(user_id):
        return current_app.mongo.db.users.find_one({"_id": ObjectId(user_id)})


class Notification:
    @staticmethod
    def create(data):
        data["created_at"] = datetime.utcnow()
        data["is_read"] = False
        return current_app.mongo.db.notifications.insert_one(data)


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


# -----------------------------
# Test route
# -----------------------------
@bp.route("/ping")
def ping():
    return jsonify({"message": "agent blueprint active!"}), 200


# -----------------------------
# Agent: Create House
# -----------------------------


def convert_objectid(obj):
    """Recursively convert all ObjectIds in dict/list to strings."""
    if isinstance(obj, list):
        return [convert_objectid(item) for item in obj]
    elif isinstance(obj, dict):
        return {k: convert_objectid(v) for k, v in obj.items()}
    elif isinstance(obj, ObjectId):
        return str(obj)
    else:
        return obj

@bp.route("/create-house", methods=["POST"])
@jwt_required()
@role_required("agent")
def create_house():
    user = g.user
    form = request.form

    # Validate required fields
    title = form.get("title")
    description = form.get("description")
    location = form.get("location")
    price = form.get("price")

    if not all([title, description, location, price]):
        return jsonify({"error": "All fields are required."}), 400

    if "image" not in request.files:
        return jsonify({"error": "House image is required."}), 400

    file = request.files["image"]
    if not file or file.filename == "":
        return jsonify({"error": "No file selected."}), 400

    if not allowed_file(file.filename):
        return jsonify({"error": "Invalid image type."}), 400

    # Save image
    folder = os.path.join(current_app.root_path, "uploads", "house_images")
    os.makedirs(folder, exist_ok=True)

    filename = secure_filename(
        f"{user['_id']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}"
    )
    file_path = os.path.join(folder, filename)
    file.save(file_path)

    # Prepare data for MongoDB
    data = {
        "agent_id": user["_id"],  # store as ObjectId if your DB expects it
        "title": title,
        "description": description,
        "location": location,
        "price": float(price),
        "image_path": f"/uploads/house_images/{filename}",
        "created_at": datetime.utcnow(),
        "status": "pending",
    }

    # Insert into MongoDB
    result = House.create(data)  # result.inserted_id is ObjectId

    # Convert all ObjectIds in response to strings
    house_data = convert_objectid({**data, "id": result.inserted_id})

    return jsonify({
        "message": "House created successfully!",
        "house": house_data
    }), 201



# -----------------------------
# Agent: Get My Houses
# -----------------------------
@bp.route("/my-houses", methods=["GET"])
@jwt_required()
@role_required("agent")
def my_houses():
    user = g.user
    houses = House.find_by_agent(user["_id"])

    for h in houses:
        h["id"] = str(h["_id"])
        h.pop("_id", None)

    return jsonify({"total_houses": len(houses), "houses": houses}), 200


# -----------------------------
# Agent: Edit House
# -----------------------------
@bp.route("/edit-house/<house_id>", methods=["PUT"])
@jwt_required()
@role_required("agent")
def edit_house(house_id):
    user = g.user
    oid = ObjectId(house_id)
    house = current_app.mongo.db.houses.find_one({"_id": oid, "agent_id": str(user["_id"])})

    if not house:
        return jsonify({"error": "House not found or unauthorized."}), 404

    form = request.form
    updates = {
        "title": form.get("title", house["title"]),
        "description": form.get("description", house["description"]),
        "location": form.get("location", house["location"]),
        "price": float(form.get("price", house["price"]))
    }

    if "image" in request.files:
        file = request.files["image"]
        if file and allowed_file(file.filename):
            folder = os.path.join(current_app.root_path, "uploads", "house_images")
            os.makedirs(folder, exist_ok=True)
            filename = secure_filename(f"{user['_id']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}_{file.filename}")
            file_path = os.path.join(folder, filename)
            file.save(file_path)
            updates["image_path"] = f"/uploads/house_images/{filename}"

    current_app.mongo.db.houses.update_one({"_id": oid}, {"$set": updates})
    return jsonify({"message": "House updated successfully!"}), 200


# -----------------------------
# Agent: Delete House
# -----------------------------
@bp.route("/delete-house/<house_id>", methods=["DELETE"])
@jwt_required()
@role_required("agent")
def delete_house(house_id):
    user = g.user
    oid = ObjectId(house_id)
    result = current_app.mongo.db.houses.delete_one({"_id": oid, "agent_id": str(user["_id"])})

    if result.deleted_count == 0:
        return jsonify({"error": "House not found or unauthorized."}), 404

    return jsonify({"message": "House deleted successfully."}), 200


# -----------------------------
# Admin: View All Houses
# -----------------------------
@bp.route("/all-houses", methods=["GET"])
@jwt_required()
@admin_required
def all_houses():
    houses = House.find_all()
    data = []

    for h in houses:
        agent = User.find_by_id(h["agent_id"])
        h["id"] = str(h["_id"])
        h.pop("_id", None)
        h["agent"] = {
            "id": h["agent_id"],
            "name": agent.get("username") if agent else "Deleted User",
            "email": agent.get("email") if agent else "N/A"
        }
        data.append(h)

    return jsonify({"total_houses": len(data), "houses": data}), 200


# -----------------------------
# Admin: Review House
# -----------------------------
@bp.route("/review-house/<house_id>", methods=["POST"])
@jwt_required()
@admin_required
def review_house(house_id):
    data = request.get_json()
    decision = data.get("decision")
    note = data.get("note", "")

    if decision not in ["approved", "rejected"]:
        return jsonify({"error": "Decision must be 'approved' or 'rejected'"}), 400

    house = current_app.mongo.db.houses.find_one({"_id": ObjectId(house_id)})
    if not house:
        return jsonify({"error": "House not found"}), 404

    House.update_status(house_id, decision)

    msg = f"Your house '{house['title']}' has been {decision.upper()}. {note}"
    Notification.create({"user_id": house["agent_id"], "message": msg})

    return jsonify({"message": f"House '{house['title']}' {decision} successfully.", "note": note}), 200
