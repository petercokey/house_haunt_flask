# app/routes/haunter.py
from flask import Blueprint, jsonify, g, request
from datetime import datetime
from bson import ObjectId
from app import mongo
from app.utils.decorators import role_required
from app.utils.auth_helpers import jwt_required
from app.utils.notify import create_notification

bp = Blueprint("haunter", __name__, url_prefix="/api/haunter")


@bp.route("/ping")
def ping():
    return jsonify({"message": "haunter blueprint active!"}), 200


# Get All Approved Houses
@bp.route("/houses", methods=["GET"])
@jwt_required()
@role_required("haunter")
def get_all_houses():
    houses = list(mongo.db.houses.find({"status": "approved"}).sort("created_at", -1))
    result = []

    base_url = request.host_url.rstrip("/")

    for house in houses:
        agent = mongo.db.users.find_one({"_id": house["agent_id"]})

        image_path = house.get("image_path")
        image_url = f"{base_url}{image_path}" if image_path else None

        result.append({
            "id": str(house["_id"]),
            "title": house["title"],
            "price": house["price"],
            "location": house["location"],
            "description": house.get("description"),
            "image_url": image_url,
            "agent_name": agent["username"] if agent else "Unknown",
            "created_at": house.get("created_at")
        })

    return jsonify({"houses": result}), 200



# House Details
@bp.route("/house/<house_id>", methods=["GET"])
@jwt_required()
@role_required("haunter")
def get_house_details(house_id):
    house = mongo.db.houses.find_one({"_id": ObjectId(house_id), "status": "approved"})
    if not house:
        return jsonify({"error": "House not found or not approved."}), 404

    agent = mongo.db.users.find_one({"_id": house["agent_id"]}) if house.get("agent_id") else None
    return jsonify({
        "id": str(house["_id"]),
        "title": house["title"],
        "description": house.get("description"),
        "location": house["location"],
        "price": house["price"],
        "image_url": house.get("image_path"),
        "agent": {
            "id": str(agent["_id"]) if agent else None,
            "name": agent["username"] if agent else "Unknown Agent",
            "email": agent.get("email") if agent else None,
        },
        "created_at": house.get("created_at")
    }), 200


# Contact Agent (deduct credits)
@bp.route("/contact-agent/<house_id>", methods=["POST"])
@jwt_required()
@role_required("haunter")
def contact_agent(house_id):
    user_id = g.user["_id"]
    house = mongo.db.houses.find_one({"_id": ObjectId(house_id), "status": "approved"})
    if not house:
        return jsonify({"error": "House not found or not approved."}), 404

    wallet = mongo.db.wallets.find_one({"user_id": user_id})
    if not wallet or wallet.get("balance", 0) < 2:
        return jsonify({"error": "Insufficient credits"}), 402

    new_balance = wallet.get("balance", 0) - 2
    mongo.db.wallets.update_one({"_id": wallet["_id"]}, {"$set": {"balance": new_balance}})

    mongo.db.transactions.insert_one({
        "user_id": user_id,
        "amount": -2,
        "txn_type": "deduction",
        "description": f"Requested contact info for '{house['title']}'",
        "created_at": datetime.utcnow()
    })

    mongo.db.contact_requests.insert_one({
        "haunter_id": user_id,
        "agent_id": house["agent_id"],
        "house_id": house["_id"],
        "created_at": datetime.utcnow()
    })

    create_notification(house["agent_id"], f"A haunter requested contact for '{house['title']}'.")
    create_notification(user_id, f"2 credits deducted for contacting '{house['title']}'.")

    return jsonify({"message": f"Contact request sent for '{house['title']}'.", "remaining_balance": new_balance}), 201


# Toggle Favorite
@bp.route("/favorite/<house_id>", methods=["POST"])
@jwt_required()
@role_required("haunter")
def toggle_favorite(house_id):
    user_id = g.user["_id"]
    house_oid = ObjectId(house_id)
    fav = mongo.db.favorites.find_one({"haunter_id": user_id, "house_id": house_oid})

    if fav:
        mongo.db.favorites.delete_one({"_id": fav["_id"]})
        return jsonify({"message": "Removed from favorites."}), 200

    mongo.db.favorites.insert_one({"haunter_id": user_id, "house_id": house_oid, "created_at": datetime.utcnow()})
    return jsonify({"message": "Added to favorites."}), 201


# Get all favorites
@bp.route("/favorites", methods=["GET"])
@jwt_required()
@role_required("haunter")
def get_favorites():
    user_id = g.user["_id"]
    favorites = list(mongo.db.favorites.find({"haunter_id": user_id}))
    results = []
    for f in favorites:
        house = mongo.db.houses.find_one({"_id": f["house_id"], "status": "approved"})
        if house:
            results.append({
                "id": str(house["_id"]),
                "title": house["title"],
                "location": house["location"],
                "price": house["price"],
                "image_url": house.get("image_path")
            })
    return jsonify({"total_favorites": len(results), "favorites": results}), 200
