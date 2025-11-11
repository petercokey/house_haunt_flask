# app/routes/notifications.py
from flask import Blueprint, jsonify, g
from datetime import datetime
from bson import ObjectId
from app import mongo
from app.utils.auth_helpers import jwt_required

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


@bp.route("/ping")
def ping():
    return jsonify({"message": "Notifications blueprint active!"}), 200


# Fetch all notifications
@bp.route("/", methods=["GET"])
@jwt_required()
def get_notifications():
    user_id = g.user["_id"]
    notifications = list(mongo.db.notifications.find({"user_id": user_id}).sort("created_at", -1))

    results = [{
        "id": str(n["_id"]),
        "message": n.get("message"),
        "is_read": n.get("is_read", False),
        "created_at": n.get("created_at")
    } for n in notifications]

    return jsonify({"total": len(results), "notifications": results}), 200


# Mark single as read
@bp.route("/mark-read/<notification_id>", methods=["PATCH"])
@jwt_required()
def mark_as_read(notification_id):
    user_id = g.user["_id"]
    result = mongo.db.notifications.update_one(
        {"_id": ObjectId(notification_id), "user_id": user_id},
        {"$set": {"is_read": True}}
    )
    if result.matched_count == 0:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify({"message": "Notification marked as read."}), 200


# Mark all as read
@bp.route("/mark-all-read", methods=["PATCH"])
@jwt_required()
def mark_all_read():
    user_id = g.user["_id"]
    result = mongo.db.notifications.update_many(
        {"user_id": user_id, "is_read": False},
        {"$set": {"is_read": True}}
    )
    return jsonify({"message": f"{result.modified_count} notifications marked as read."}), 200


# Delete single notification
@bp.route("/delete/<notification_id>", methods=["DELETE"])
@jwt_required()
def delete_notification(notification_id):
    user_id = g.user["_id"]
    result = mongo.db.notifications.delete_one({"_id": ObjectId(notification_id), "user_id": user_id})
    if result.deleted_count == 0:
        return jsonify({"error": "Notification not found"}), 404
    return jsonify({"message": "Notification deleted successfully."}), 200


# Clear all notifications
@bp.route("/clear", methods=["DELETE"])
@jwt_required()
def clear_notifications():
    user_id = g.user["_id"]
    mongo.db.notifications.delete_many({"user_id": user_id})
    return jsonify({"message": "All notifications cleared."}), 200
