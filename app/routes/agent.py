from flask import Blueprint, jsonify, request, g
from datetime import datetime
from bson import ObjectId
from app.extensions import mongo
from app.utils.auth_helpers import jwt_required, role_required
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

@bp.route("/contact-requests", methods=["GET"])
@jwt_required()
@role_required("agent")
def get_contact_requests():
    agent_id = g.user["_id"]

    requests = list(
        mongo.db.contact_requests.find({"agent_id": agent_id})
        .sort("created_at", -1)
    )

    results = []

    for req in requests:
        haunter = mongo.db.users.find_one(
            {"_id": req["haunter_id"], "role": "haunter"},
            {"password": 0}  # never expose passwords
        )

        house = mongo.db.houses.find_one(
            {"_id": req["house_id"]},
            {"title": 1, "location": 1, "price": 1}
        )

        results.append({
            "request_id": str(req["_id"]),
            "created_at": req.get("created_at"),

            "haunter": {
                "id": str(haunter["_id"]) if haunter else None,
                "username": haunter.get("username") if haunter else "Unknown",
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

@bp.route("/agent/contact-requests/<request_id>/decision", methods=["OPTIONS"])
def contact_decision_options(request_id):
    return ("", 204)


@bp.route("/contact-requests/<request_id>/decision", methods=["POST"])
@jwt_required()
@role_required("agent")
def decide_contact_request(request_id):
    agent_id = g.user["_id"]
    data = request.get_json() or {}
    decision = data.get("decision")

    if decision not in ("accepted", "rejected"):
        return jsonify({"error": "Decision must be accepted or rejected"}), 400

    contact_request = mongo.db.contact_requests.find_one({
        "_id": ObjectId(request_id),
        "agent_id": agent_id,
    })

    if not contact_request:
        return jsonify({"error": "Contact request not found"}), 404

    # Prevent double decisions
    if contact_request.get("status") in ("accepted", "rejected"):
        return jsonify({"error": "Request already decided"}), 409

    mongo.db.contact_requests.update_one(
        {"_id": ObjectId(request_id)},
        {"$set": {
            "status": decision,
            "responded_at": datetime.utcnow(),
        }}
    )

    # ✅ CREATE CHAT ON ACCEPT
    if decision == "accepted":
        existing_chat = mongo.db.chats.find_one({
            "contact_request_id": ObjectId(request_id)
        })

        if not existing_chat:
            mongo.db.chats.insert_one({
                "contact_request_id": ObjectId(request_id),
                "agent_id": agent_id,
                "haunter_id": contact_request["haunter_id"],
                "created_at": datetime.utcnow(),
            })

    return jsonify({
        "message": f"Contact request {decision}"
    }), 200


@bp.route("/chats", methods=["GET"])
@jwt_required()
@role_required("agent")
def get_agent_chats():
    agent_id = g.user["_id"]

    chats = list(
        mongo.db.chats.find({"agent_id": agent_id})
        .sort("created_at", -1)
    )

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
                "username": haunter.get("username") if haunter else "Unknown",
                "email": haunter.get("email") if haunter else None,
            }
        })

    return jsonify({
        "total": len(results),
        "chats": results
    }), 200

@bp.route("/chats/<chat_id>/messages", methods=["POST"])
@jwt_required()
@role_required("agent")
def send_chat_message(chat_id):
    agent_id = g.user["_id"]
    data = request.get_json() or {}
    content = data.get("content")

    if not content:
        return jsonify({"error": "Message content required"}), 400

    chat = mongo.db.chats.find_one({
        "_id": ObjectId(chat_id),
        "agent_id": agent_id,
    })

    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    mongo.db.messages.insert_one({
        "chat_id": ObjectId(chat_id),
        "sender_id": agent_id,
        "sender_role": "agent",
        "content": content,
        "created_at": datetime.utcnow(),
    })

    return jsonify({"message": "Message sent"}), 201
@bp.route("/chats/<chat_id>/messages", methods=["GET"])
@jwt_required()
@role_required("agent")
def get_chat_messages(chat_id):
    agent_id = g.user["_id"]

    chat = mongo.db.chats.find_one({
        "_id": ObjectId(chat_id),
        "agent_id": agent_id,
    })

    if not chat:
        return jsonify({"error": "Chat not found"}), 404

    messages = list(
        mongo.db.messages
        .find({"chat_id": ObjectId(chat_id)})
        .sort("created_at", 1)
    )

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
