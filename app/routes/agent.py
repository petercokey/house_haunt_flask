from flask import Blueprint, jsonify, request, g
from datetime import datetime
from bson import ObjectId
from app import mongo
from app.utils.auth_helpers import jwt_required
from app.utils.decorators import role_required
from app.utils.image_uploader import upload_house_image

bp = Blueprint("agent", __name__, url_prefix="/api/agent")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


@bp.route("/ping")
def ping():
    return jsonify({"message": "agent blueprint active!"}), 200


# ===============================
# CREATE HOUSE (MULTIPLE IMAGES)
# ===============================
@bp.route("/create-house", methods=["POST"])
@jwt_required()
@role_required("agent")
def create_house():
    user = g.user
    form = request.form

    title = form.get("title")
    description = form.get("description")
    location = form.get("location")
    price = form.get("price")

    if not all([title, description, location, price]):
        return jsonify({"error": "All fields are required."}), 400

    if "images" not in request.files:
        return jsonify({"error": "At least one image is required."}), 400

    files = request.files.getlist("images")

    if not files or len(files) == 0:
        return jsonify({"error": "No images selected."}), 400

    image_urls = []

    for file in files:
        if file and allowed_file(file.filename):
            public_id = f"{user['_id']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
            url = upload_house_image(file, public_id)
            image_urls.append(url)

    if len(image_urls) == 0:
        return jsonify({"error": "Invalid image types."}), 400

    data = {
        "agent_id": user["_id"],
        "title": title,
        "description": description,
        "location": location,
        "price": float(price),
        "images": image_urls,        # ✅ MULTIPLE IMAGES
        "created_at": datetime.utcnow(),
        "status": "pending",
    }

    result = mongo.db.houses.insert_one(data)

    return jsonify({
        "message": "House created successfully",
        "house_id": str(result.inserted_id),
    }), 201


# ===============================
# MY HOUSES
# ===============================
@bp.route("/my-houses", methods=["GET"])
@jwt_required()
@role_required("agent")
def my_houses():
    houses = list(mongo.db.houses.find({"agent_id": g.user["_id"]}))

    for h in houses:
        h["id"] = str(h["_id"])
        h["agent_id"] = str(h["agent_id"])
        h.pop("_id", None)

    return jsonify({"houses": houses}), 200


# ===============================
# EDIT HOUSE (ADD MORE IMAGES)
# ===============================
@bp.route("/edit-house/<house_id>", methods=["PUT"])
@jwt_required()
@role_required("agent")
def edit_house(house_id):
    oid = ObjectId(house_id)

    house = mongo.db.houses.find_one({
        "_id": oid,
        "agent_id": g.user["_id"],
    })

    if not house:
        return jsonify({"error": "House not found"}), 404

    updates = {
        "title": request.form.get("title", house["title"]),
        "description": request.form.get("description", house["description"]),
        "location": request.form.get("location", house["location"]),
        "price": float(request.form.get("price", house["price"])),
    }

    # ✅ ADD NEW IMAGES (APPEND)
    if "images" in request.files:
        files = request.files.getlist("images")
        new_images = []

        for file in files:
            if file and allowed_file(file.filename):
                public_id = f"{g.user['_id']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
                new_images.append(upload_house_image(file, public_id))

        if new_images:
            updates["images"] = house.get("images", []) + new_images

    mongo.db.houses.update_one({"_id": oid}, {"$set": updates})

    return jsonify({"message": "House updated"}), 200


# ===============================
# DELETE HOUSE
# ===============================
@bp.route("/delete-house/<house_id>", methods=["DELETE"])
@jwt_required()
@role_required("agent")
def delete_house(house_id):
    result = mongo.db.houses.delete_one({
        "_id": ObjectId(house_id),
        "agent_id": g.user["_id"],
    })

    if result.deleted_count == 0:
        return jsonify({"error": "House not found"}), 404

    return jsonify({"message": "House deleted"}), 200
