from flask import Blueprint, jsonify, request
from flask_login import login_required, current_user
 Notification

bp = Blueprint("notifications", __name__, url_prefix="/api/notifications")


# ðŸŸ¢ Test route
@bp.route("/ping")
def ping():
    return jsonify({"message": "Notifications blueprint active!"}), 200


# ðŸ”¹ Fetch all notifications for the current user
@bp.route("/", methods=["GET"])
@login_required
def get_notifications():
    """Return all notifications for the logged-in user."""
    notifications = (
        Notification.query.filter_by(user_id=current_user.id)
        .order_by(Notification.created_at.desc())
        .all()
    )

    results = [
        {
            "id": n.id,
            "message": n.message,
            "is_read": n.is_read,
            "created_at": n.created_at,
        }
        for n in notifications
    ]

    return jsonify({
        "total": len(results),
        "notifications": results
    }), 200


# ðŸ”¹ Mark a single notification as read
@bp.route("/mark-read/<int:notification_id>", methods=["PATCH"])
@login_required
def mark_as_read(notification_id):
    """Mark a specific notification as read."""
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notification:
        return jsonify({"error": "Notification not found"}), 404

    notification.is_read = True
    db.session.commit()

    return jsonify({"message": "Notification marked as read."}), 200


# ðŸ”¹ Mark all notifications as read
@bp.route("/mark-all-read", methods=["PATCH"])
@login_required
def mark_all_read():
    """Mark all notifications for the user as read."""
    updated = (
        Notification.query.filter_by(user_id=current_user.id, is_read=False)
        .update({"is_read": True})
    )
    db.session.commit()

    return jsonify({"message": f"{updated} notifications marked as read."}), 200


# ðŸ”¹ Delete a single notification
@bp.route("/delete/<int:notification_id>", methods=["DELETE"])
@login_required
def delete_notification(notification_id):
    """Allow users to delete a specific notification."""
    notification = Notification.query.filter_by(id=notification_id, user_id=current_user.id).first()
    if not notification:
        return jsonify({"error": "Notification not found"}), 404

    db.session.delete(notification)
    db.session.commit()
    return jsonify({"message": "Notification deleted successfully."}), 200


# ðŸ”¹ Clear all notifications
@bp.route("/clear", methods=["DELETE"])
@login_required
def clear_notifications():
    """Delete all notifications for the logged-in user."""
    Notification.query.filter_by(user_id=current_user.id).delete()
    db.session.commit()

    return jsonify({"message": "All notifications cleared."}), 200

