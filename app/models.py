# app/models.py
from datetime import datetime
from flask import current_app
from bson import ObjectId

# ðŸ”¹ Utility function to get MongoDB collections
def get_collection(name):
    return current_app.mongo.db[name]

# ==========================================================
# ðŸ”¹ USER MODEL
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
        return get_collection(User.collection).find_one({"_id": ObjectId(user_id)})

    @staticmethod
    def update(user_id, updates):
        return get_collection(User.collection).update_one(
            {"_id": ObjectId(user_id)}, {"$set": updates}
        )


# ==========================================================
# ðŸ”¹ HOUSE MODEL
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
        return get_collection(House.collection).find_one({"_id": ObjectId(house_id)})

    @staticmethod
    def update_status(house_id, status):
        return get_collection(House.collection).update_one(
            {"_id": ObjectId(house_id)}, {"$set": {"status": status}}
        )


# ==========================================================
# ðŸ”¹ CONTACT REQUEST MODEL
# ==========================================================
class ContactRequest:
    collection = "contact_requests"

    @staticmethod
    def create(data):
        data["created_at"] = datetime.utcnow()
        data["status"] = "pending"
        return get_collection(ContactRequest.collection).insert_one(data)


# ==========================================================
# ðŸ”¹ FAVORITE MODEL
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
        else:
            doc = {"haunter_id": haunter_id, "house_id": house_id, "created_at": datetime.utcnow()}
            coll.insert_one(doc)
            return {"message": "Added to favorites"}

    @staticmethod
    def find_all_for_haunter(haunter_id):
        return list(get_collection(Favorite.collection).find({"haunter_id": haunter_id}))


# ==========================================================
# ðŸ”¹ REVIEW MODEL
# ==========================================================
class Review:
    collection = "reviews"

    @staticmethod
    def create(data):
        data["created_at"] = datetime.utcnow()
        data["is_flagged"] = False
        return get_collection(Review.collection).insert_one(data)

    @staticmethod
    def find_for_agent(agent_id):
        return list(get_collection(Review.collection).find({"agent_id": agent_id}))


# ==========================================================
# ðŸ”¹ KYC MODEL
# ==========================================================
class KYC:
    collection = "kyc"

    @staticmethod
    def create(data):
        data["submitted_at"] = datetime.utcnow()
        data["status"] = "pending"
        return get_collection(KYC.collection).insert_one(data)

    @staticmethod
    def find_for_agent(agent_id):
        return get_collection(KYC.collection).find_one({"agent_id": agent_id})


# ==========================================================
# ðŸ”¹ NOTIFICATION MODEL
# ==========================================================
class Notification:
    collection = "notifications"

    @staticmethod
    def create(data):
        data["created_at"] = datetime.utcnow()
        data["is_read"] = False
        return get_collection(Notification.collection).insert_one(data)

    @staticmethod
    def find_for_user(user_id):
        return list(get_collection(Notification.collection).find({"user_id": user_id}))


# ==========================================================
# ðŸ”¹ WALLET MODEL
# ==========================================================
class Wallet:
    collection = "wallets"

    @staticmethod
    def get_or_create(user_id):
        wallet = get_collection(Wallet.collection).find_one({"user_id": user_id})
        if not wallet:
            wallet = {"user_id": user_id, "balance": 0.0, "updated_at": datetime.utcnow()}
            get_collection(Wallet.collection).insert_one(wallet)
        return wallet

    @staticmethod
    def update_balance(user_id, amount):
        wallet = Wallet.get_or_create(user_id)
        new_balance = float(wallet["balance"]) + float(amount)
        get_collection(Wallet.collection).update_one(
            {"user_id": user_id},
            {"$set": {"balance": new_balance, "updated_at": datetime.utcnow()}},
        )
        return new_balance


# ==========================================================
# ðŸ”¹ TRANSACTION MODEL
# ==========================================================
class Transaction:
    collection = "transactions"

    @staticmethod
    def create(data):
        data["created_at"] = datetime.utcnow()
        return get_collection(Transaction.collection).insert_one(data)

    @staticmethod
    def find_for_user(user_id):
        return list(get_collection(Transaction.collection).find({"user_id": user_id}))
