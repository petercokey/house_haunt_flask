# app/models.py
from datetime import datetime
from flask import current_app
from bson import ObjectId

def get_collection(name):
    """Get a MongoDB collection safely."""
    return current_app.mongo.db[name]

def to_objectid(id_str):
    """Safely convert string to ObjectId, return None if invalid."""
    try:
        return ObjectId(id_str)
    except Exception:
        return None

# ==========================================================
# USER MODEL
# ==========================================================
class User:
    collection = "users"

    @staticmethod
    def create(data):
        data["created_at"] = datetime.utcnow()
        return get_collection(User.collection).insert_one(data)

    @staticmethod
    def find_by_email(email):
        return get_collection(User.collection).find_one({"email": email})

    @staticmethod
    def find_by_id(user_id):
        oid = to_objectid(user_id)
        return get_collection(User.collection).find_one({"_id": oid}) if oid else None

    @staticmethod
    def update(user_id, updates):
        oid = to_objectid(user_id)
        if not oid:
            return None
        return get_collection(User.collection).update_one({"_id": oid}, {"$set": updates})

# ==========================================================
# HOUSE MODEL
# ==========================================================
class House:
    collection = "houses"

    @staticmethod
    def create(data):
        data["created_at"] = datetime.utcnow()
        data["status"] = data.get("status", "pending")
        return get_collection(House.collection).insert_one(data)

    @staticmethod
    def find_all_approved():
        return list(get_collection(House.collection).find({"status": "approved"}))

    @staticmethod
    def find_by_id(house_id):
        oid = to_objectid(house_id)
        return get_collection(House.collection).find_one({"_id": oid}) if oid else None

    @staticmethod
    def update_status(house_id, status):
        oid = to_objectid(house_id)
        if not oid:
            return None
        return get_collection(House.collection).update_one(
            {"_id": oid}, {"$set": {"status": status}}
        )

# ==========================================================
# CONTACT REQUEST MODEL
# ==========================================================
class ContactRequest:
    collection = "contact_requests"

    @staticmethod
    def create(data):
        data.update({"created_at": datetime.utcnow(), "status": "pending"})
        return get_collection(ContactRequest.collection).insert_one(data)

# ==========================================================
# FAVORITE MODEL
# ==========================================================
class Favorite:
    collection = "favorites"

    @staticmethod
    def toggle(haunter_id, house_id):
        coll = get_collection(Favorite.collection)
        existing = coll.find_one({"haunter_id": haunter_id, "house_id": house_id})
        if existing:
            coll.delete_one({"_id": existing["_id"]})
            return {"message": "Removed from favorites"}
        doc = {"haunter_id": haunter_id, "house_id": house_id, "created_at": datetime.utcnow()}
        coll.insert_one(doc)
        return {"message": "Added to favorites"}

    @staticmethod
    def find_all_for_haunter(haunter_id):
        return list(get_collection(Favorite.collection).find({"haunter_id": haunter_id}))

# ==========================================================
# REVIEW MODEL
# ==========================================================
class Review:
    collection = "reviews"

    @staticmethod
    def create(data):
        data.update({"created_at": datetime.utcnow(), "is_flagged": False})
        return get_collection(Review.collection).insert_one(data)

    @staticmethod
    def find_for_agent(agent_id):
        return list(get_collection(Review.collection).find({"agent_id": agent_id}).sort("created_at", -1))

# ==========================================================
# KYC MODEL
# ==========================================================
class KYC:
    collection = "kyc"

    @staticmethod
    def create(data):
        data.update({"submitted_at": datetime.utcnow(), "status": "pending"})
        return get_collection(KYC.collection).insert_one(data)

    @staticmethod
    def find_for_agent(agent_id):
        return get_collection(KYC.collection).find_one({"agent_id": agent_id})

# ==========================================================
# NOTIFICATION MODEL
# ==========================================================
class Notification:
    collection = "notifications"

    @staticmethod
    def create(data):
        data.update({"created_at": datetime.utcnow(), "is_read": False})
        return get_collection(Notification.collection).insert_one(data)

    @staticmethod
    def find_for_user(user_id):
        return list(get_collection(Notification.collection).find({"user_id": user_id}).sort("created_at", -1))

# ==========================================================
# WALLET MODEL
# ==========================================================
class Wallet:
    collection = "wallets"

    @staticmethod
    def get_or_create(user_id):
        coll = get_collection(Wallet.collection)
        wallet = coll.find_one({"user_id": user_id})
        if not wallet:
            wallet = {"user_id": user_id, "balance": 0.0, "updated_at": datetime.utcnow()}
            coll.insert_one(wallet)
        return wallet

    @staticmethod
    def update_balance(user_id, amount):
        coll = get_collection(Wallet.collection)
        wallet = Wallet.get_or_create(user_id)
        new_balance = float(wallet["balance"]) + float(amount)
        coll.update_one(
            {"user_id": user_id},
            {"$set": {"balance": new_balance, "updated_at": datetime.utcnow()}},
        )
        return new_balance

# ==========================================================
# TRANSACTION MODEL
# ==========================================================
class Transaction:
    collection = "transactions"

    @staticmethod
    def create(data):
        data["created_at"] = datetime.utcnow()
        return get_collection(Transaction.collection).insert_one(data)

    @staticmethod
    def find_for_user(user_id):
        return list(get_collection(Transaction.collection).find({"user_id": user_id}).sort("created_at", -1))
