from flask import Blueprint, jsonify, request, g
from flask_login import login_required, current_user
from app.utils.decorators import role_required
from app.utils.auth_helpers import jwt_required
from datetime import datetime
from app import mongo
from bson import ObjectId

from app.models import (
    Favorite,
    House,
    User
)
bp = Blueprint("favorites", __name__, url_prefix="/api/favorites")

@bp.route("/ping")
def ping():
    return jsonify({"message": "favorites blueprint active!"}), 200
# Get all favorites for logged-in haunter
@bp.route("/", methods=["GET"])
@jwt_required()
@role_required("haunter")
def get_favorites():
    haunter_id = g.user["_id"]
    favorites = list(mongo.db.favorites.find({"haunter_id": haunter_id}))

    results = []
    for fav in favorites:
        house = mongo.db.houses.find_one({"_id": fav["house_id"], "status": "approved"})
        if house:
            results.append({
                "id": str(house["_id"]),
                "title": house["title"],
                "location": house["location"],
                "price": house["price"],
                "image_url": house.get("image_path")
            })

    return jsonify({"total_favorites": len(results), "favorites": results}), 200


# Add to favorites
@bp.route("/add/<house_id>", methods=["POST"])
@jwt_required()
@role_required("haunter")
def add_favorite(house_id):
    house_oid = ObjectId(house_id)
    haunter_id = g.user["_id"]

    if mongo.db.favorites.find_one({"haunter_id": haunter_id, "house_id": house_oid}):
        return jsonify({"message": "House already in favorites."}), 200

    mongo.db.favorites.insert_one({"haunter_id": haunter_id, "house_id": house_oid})
    return jsonify({"message": "House added to favorites!"}), 201


# Remove from favorites
@bp.route("/remove/<house_id>", methods=["DELETE"])
@jwt_required()
@role_required("haunter")
def remove_favorite(house_id):
    house_oid = ObjectId(house_id)
    haunter_id = g.user["_id"]

    fav = mongo.db.favorites.find_one({"haunter_id": haunter_id, "house_id": house_oid})
    if not fav:
        return jsonify({"error": "House not in favorites."}), 404

    mongo.db.favorites.delete_one({"_id": fav["_id"]})
    return jsonify({"message": "House removed from favorites."}), 200
