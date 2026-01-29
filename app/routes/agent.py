from flask import Blueprint, jsonify, request, g
from datetime import datetime
from bson import ObjectId
from bson.errors import InvalidId

from app.extensions import mongo
from app.utils.auth_helpers import jwt_required, role_required
from app.utils.image_uploader import upload_house_image

bp = Blueprint("agent", __name__, url_prefix="/api/agent")

ALLOWED_EXTENSIONS = {"png", "jpg", "jpeg", "webp"}


# ===============================
# HELPERS
# ===============================
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_EXTENSIONS


def parse_object_id(value, error_msg):
    try:
        return ObjectId(value)
    except InvalidId:
        return None


# ===============================
# PING
# ===============================
@bp.route("/ping", methods=["GET"])
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
        return jsonify({"error": "All fields are required"}), 400

    if "images" not in request.files:
        return jsonify({"error": "At least one image is required"}), 400

    files = request.files.getlist("images")
    image_urls = []

    for file in files:
        if file and allowed_file(file.filename):
            public_id = f"{user['_id']}_{datetime.utcnow().strftime('%Y%m%d%H%M%S%f')}"
            image_urls.append(upload_house_image(file, public_id))

    if not image_urls:
        return jsonify({"error": "Invalid image types"}), 400

    house = {
        "agent_id": user["_id"],
        "title": title,
        "description": description,
        "location": location,
        "price": float(price),
        "images": image_urls,
        "created_at": datetime.utcnow(),
        "status": "pending",
    }

    result = mongo.db.houses.insert_one(house)

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
    houses = mongo.db.houses.find({"agent_id": g.user["_id"]})

    results = []
    for h in houses:
        h["id"] = str(h["_id"])
        h["agent_id"] = str(h["agent_id"])
        h.pop("_id", None)
        results.append(h)

    return jsonify({"houses": results}), 200


# ===============================
# EDIT HOUSE
# ===============================
@bp.route("/edit-house/<house_id>", methods=["PUT"])
@jwt_required()
@role_required("agent")
def edit_house(house_id):
    oid = parse_object_id(house_id, "Invalid house id")
    if not oid:
        return jsonify({"error": "Invalid house id"}), 400

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

    if "images" in request.files:
        new_images = []
        for file in request.files.getlist("images"):
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
    oid = parse_object_id(house_id, "Invalid house id")
    if not oid:
        return jsonify({"error": "Invalid house id"}), 400

    result = mongo.db.houses.delete_one({
        "_id": oid,
        "agent_id": g.user["_id"],
    })

    if result.deleted_count == 0:
        return jsonify({"error": "House not found"}), 404

    return jsonify({"message": "House deleted"}), 200


# ===============================
# GET CONTACT REQUESTS
# ===============================
@bp.route("/contact-requests", methods=["GET"])
@jwt_required()
@role_required("agent")
def get_contact_requests():
    agent_id = g.user["_id"]

    requests = mongo.db.contact_requests.find(
        {"agent_id": agent_id}
    ).sort("created_at", -1)

    results = []

    for req in requests:
        haunter = mongo.db.users.find_one(
            {"_id": req["haunter_id"]},
            {"password": 0}
        )

        house = mongo.db.houses.find_one(
            {"_id": req["house_id"]},
            {"title": 1, "location": 1, "price": 1}
        )

        results.append({
            "request_id": str(req["_id"]),
            "status": req.get("status"),
            "created_at": req.get("created_at"),
            "haunter": {
                "id": str(haunter["_id"]) if haunter else None,
                "username": haunter.get("username") if haunter else None,
                "email": haunter.get("email") if haunter else None,
            },
            "house": {
                "id": str(house["_id"]) if house else None,
                "title": house.get("title") if house else None,
                "location": house.get("location") if house else None,
                "price": house.get("price") if house else None,
            }
        })

    return jsonify({
        "total_requests": len(results),
        "requests": results
    }), 200


# ===============================
# DECIDE CONTACT REQUEST
# ===============================
@bp.route("/contact-requests/<request_id>/decision", methods=["POST"])
@jwt_required()
@role_required("agent")
def decide_contact_request(request_id):
    oid = parse_object_id(request_id, "Invalid request id")
    if not oid:
        return jsonify({"error": "Invalid contact request id"}), 400

    data = request.get_json(silent=True) or {}
    decision = data.get("decision")

    if decision not in ("accepted", "rejected"):
        return jsonify({"error": "Decision must be accepted or rejected"}), 400

    contact_request = mongo.db.contact_requests.find_one({
        "_id": oid,
        "agent_id": g.user["_id"],
    })

    if not contact_request:
        return jsonify({"error": "Contact request not found"}), 404

    if contact_request.get("status") in ("accepted", "rejected"):
        return jsonify({"error": "Request already decided"}), 409

    mongo.db.contact_requests.update_one(
        {"_id": oid},
        {"$set": {
            "status": decision,
            "responded_at": datetime.utcnow(),
        }}
    )

    if decision == "accepted":
        if not mongo.db.chats.find_one({"contact_request_id": oid}):
            mongo.db.chats.insert_one({
                "contact_request_id": oid,
                "agent_id": g.user["_id"],
                "haunter_id": contact_request["haunter_id"],
                "created_at": datetime.utcnow(),
            })

    return jsonify({"message": f"Contact request {decision}"}), 200


# ===============================
# AGENT CHATS
# ===============================
@bp.route("/chats", methods=["GET"])
@jwt_required()
@role_required("agent")
def get_agent_chats():
    chats = mongo.db.chats.find(
        {"agent_id": g.user["_id"]}
    ).sort("created_at", -1)

    results = []
    for chat in chats:
        haunter = mongo.db.users.find_one(
            {"_id": chat["haunter_id"]},
            {"username": 1, "email": 1}
        )

        results.append({
            "chat_id": str(chat["_id"]),
            "created_at": chat["created_at"],
            "haunter": {
                "id": str(haunter["_id"]) if haunter else None,
                "username": haunter.get("username") if haunter else None,
                "email": haunter.get("email") if haunter else None,
            }
        })

    return jsonify({"total": len(results), "chats": results}), 200


# ===============================
# CHAT MESSAGES
# ===============================
@bp.route("/chats/<chat_id>/messages", methods=["GET", "POST"])
@jwt_required()
@role_required("agent")
def chat_messages(chat_id):
    chat_oid = parse_object_id(chat_id, "Invalid chat id")
    if not chat_oid:
        return jsonify({"error": "Invalid chat id"}), 400

    chat = mongo.db.chats.find_one({
        "_id": chat_oid,
        "agent_id": g.user["_id"],
    })

    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        content = data.get("content")

        if not content:
            return jsonify({"error": "Message content required"}), 400

        mongo.db.messages.insert_one({
            "chat_id": chat_oid,
            "sender_id": g.user["_id"],
            "sender_role": "agent",
            "content": content,
            "created_at": datetime.utcnow(),
        })

        return jsonify({"message": "Message sent"}), 201

    messages = mongo.db.messages.find(
        {"chat_id": chat_oid}
    ).sort("created_at", 1)

    return jsonify({
        "messages": [
            {
                "id": str(m["_id"]),
                "sender_role": m["sender_role"],
                "content": m["content"],
                "created_at": m["created_at"]
            }
            for m in messages
        ]
    }), 200
