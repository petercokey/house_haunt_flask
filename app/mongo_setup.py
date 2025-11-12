# app/mongo_setup.py
from app import mongo
from pymongo import ASCENDING, DESCENDING

def create_indexes():
    db = mongo.db

    # =========================
    # USERS
    # =========================
    db.users.create_index([("email", ASCENDING)], unique=True)  # unique emails
    db.users.create_index([("role", ASCENDING)])
    db.users.create_index([("created_at", DESCENDING)])

    # =========================
    # HOUSES
    # =========================
    db.houses.create_index([("status", ASCENDING)])
    db.houses.create_index([("agent_id", ASCENDING)])
    db.houses.create_index([("created_at", DESCENDING)])
    db.houses.create_index([("location", ASCENDING)])
    db.houses.create_index([("price", ASCENDING)])

    # =========================
    # CONTACT REQUESTS
    # =========================
    db.contact_requests.create_index([("haunter_id", ASCENDING)])
    db.contact_requests.create_index([("agent_id", ASCENDING)])
    db.contact_requests.create_index([("house_id", ASCENDING)])
    db.contact_requests.create_index([("created_at", DESCENDING)])

    # =========================
    # FAVORITES
    # =========================
    db.favorites.create_index([("haunter_id", ASCENDING)])
    db.favorites.create_index([("house_id", ASCENDING)])

    # =========================
    # REVIEWS
    # =========================
    db.reviews.create_index([("agent_id", ASCENDING)])
    db.reviews.create_index([("haunter_id", ASCENDING)])
    db.reviews.create_index([("created_at", DESCENDING)])

    # =========================
    # KYC
    # =========================
    db.kyc.create_index([("agent_id", ASCENDING)])
    db.kyc.create_index([("status", ASCENDING)])

    # =========================
    # NOTIFICATIONS
    # =========================
    db.notifications.create_index([("user_id", ASCENDING)])
    db.notifications.create_index([("is_read", ASCENDING)])
    db.notifications.create_index([("created_at", DESCENDING)])

    # =========================
    # WALLET
    # =========================
    db.wallets.create_index([("user_id", ASCENDING)], unique=True)

    # =========================
    # TRANSACTIONS
    # =========================
    db.transactions.create_index([("user_id", ASCENDING)])
    db.transactions.create_index([("created_at", DESCENDING)])

    print("MongoDB indexes created successfully!")

# Example usage:
# from app.mongo_setup import create_indexes
# create_indexes()
