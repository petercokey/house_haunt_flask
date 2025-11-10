# app/utils/notify.py
from app import mongo
from datetime import datetime

def create_notification(user_id, message):
    """
    Create a notification for a user in MongoDB.

    Args:
        user_id (ObjectId or str): ID of the user to notify.
        message (str): Notification message.

    Returns:
        dict: The inserted notification document.
    """
    notif = {
        "user_id": user_id,
        "message": message,
        "is_read": False,
        "created_at": datetime.utcnow()
    }
    result = mongo.db.notifications.insert_one(notif)
    notif["_id"] = result.inserted_id
    return notif

