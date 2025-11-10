from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
 Favorite, House, User
from datetime import datetime
from app.utils.decorators import role_required

bp = Blueprint("favorites", __name__, url_prefix="/api/favorites")


# 🟢 Test route
@bp.route("/ping")
def ping():
    return jsonify({"message": "Favorites blueprint active!"}), 200


# 🔹 Add a house to haunter's favorites
@bp.route("/add/<int:house_id>", methods=["POST"])
@login_required
@role_required("haunter")
def add_favorite(house_id):
    """Haunter saves a house to favorites."""
    house = House.query.get(house_id)
    if not house:
        return jsonify({"error": "House not found."}), 404

    # Prevent duplicate favorites
    existing = Favorite.query.filter_by(user_id=current_user.id, house_id=house_id).first()
    if existing:
        return jsonify({"message": "House already in favorites."}), 200

    fav = Favorite(user_id=current_user.id, house_id=house_id, created_at=datetime.utcnow())
    db.session.add(fav)
    db.session.commit()

    return jsonify({"message": f"House '{house.title}' added to favorites."}), 201


# 🔹 Remove a favorite
@bp.route("/remove/<int:house_id>", methods=["DELETE"])
@login_required
@role_required("haunter")
def remove_favorite(house_id):
    """Remove a house from haunter’s favorites."""
    fav = Favorite.query.filter_by(user_id=current_user.id, house_id=house_id).first()
    if not fav:
        return jsonify({"error": "Favorite not found."}), 404

    db.session.delete(fav)
    db.session.commit()
    return jsonify({"message": "Removed from favorites."}), 200


# 🔹 Get all saved favorites
@bp.route("/", methods=["GET"])
@login_required
@role_required("haunter")
def get_favorites():
    """Return all houses a haunter has favorited."""
    favorites = (
        db.session.query(Favorite, House)
        .join(House, Favorite.house_id == House.id)
        .filter(Favorite.user_id == current_user.id)
        .order_by(Favorite.created_at.desc())
        .all()
    )

    results = []
    for fav, house in favorites:
        agent = User.query.get(house.agent_id)
        results.append({
            "favorite_id": fav.id,
            "house": {
                "id": house.id,
                "title": house.title,
                "location": house.location,
                "price": house.price,
                "image": house.image_path,
            },
            "agent": {
                "id": agent.id if agent else None,
                "name": agent.username if agent else "Unknown"
            },
            "saved_on": fav.created_at
        })

    return jsonify({
        "total_favorites": len(results),
        "favorites": results
    }), 200
