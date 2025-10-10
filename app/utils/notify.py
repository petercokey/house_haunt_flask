# app/utils/notify.py
from app.models import Notification, db
from datetime import datetime

def create_notification(user_id, message):
    """Simple helper to create and save a new notification"""
    notif = Notification(user_id=user_id, message=message, created_at=datetime.utcnow())
    db.session.add(notif)
    db.session.commit()
    return notif
