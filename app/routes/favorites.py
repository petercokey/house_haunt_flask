from flask import Blueprint, jsonify, g
from app.utils.auth_helpers import jwt_required, role_required
from app.extensions import mongo
from bson import ObjectId

bp = Blueprint("favorites", __name__, url_prefix="/api/favorites")


@bp.route("/ping")
def ping():
    return jsonify({"message": "favorites blueprint active!"}), 200


# ======================================================
# GET FAVORITES
# ======================================================
@bp.route("/", methods=["GET"])
@jwt_required()
@role_required("haunter")
def get_favorites():
    haunter_id = g.user["_id"]
    favorites = list(mongo.db.favorites.find({"haunter_id": haunter_id}))

    results = []

    for fav in favorites:
        house = mongo.db.houses.find_one({"_id": fav["house_id"]})

        if house:
            results.append({
                "favorite_id": str(fav["_id"]),        # ✅ IMPORTANT
                "house_id": str(house["_id"]),
                "title": house["title"],
                "location": house["location"],
                "price": house["price"],
                "image_url": house.get("image_url"),
                "images": house.get("images", [])
            })

    return jsonify({
        "total_favorites": len(results),
        "favorites": results
    }), 200


# ======================================================
# ADD FAVORITE
# ======================================================
@bp.route("/add/<house_id>", methods=["POST"])
@jwt_required()
@role_required("haunter")
def add_favorite(house_id):
    haunter_id = g.user["_id"]
    house_oid = ObjectId(house_id)

    if mongo.db.favorites.find_one({
        "haunter_id": haunter_id,
        "house_id": house_oid
    }):
        return jsonify({"message": "House already in favorites."}), 200

    mongo.db.favorites.insert_one({
        "haunter_id": haunter_id,
        "house_id": house_oid
    })

    return jsonify({"message": "House added to favorites!"}), 201


# ======================================================
# REMOVE FAVORITE (FIXED)
# ======================================================
@bp.route("/remove/<favorite_id>", methods=["DELETE"])
@jwt_required()
@role_required("haunter")
def remove_favorite(favorite_id):
    haunter_id = g.user["_id"]

    result = mongo.db.favorites.delete_one({
        "_id": ObjectId(favorite_id),
        "haunter_id": haunter_id
    })

    if result.deleted_count == 0:
        return jsonify({"error": "Favorite not found."}), 404

    return jsonify({"message": "House removed from favorites."}), 200
