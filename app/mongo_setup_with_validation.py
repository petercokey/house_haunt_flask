# app/mongo_setup_with_validation.py
from app import mongo
from pymongo import ASCENDING, DESCENDING

def create_indexes_and_validation():
    db = mongo.db

    # =========================
    # USERS
    # =========================
    db.users.create_index([("email", ASCENDING)], unique=True)
    db.users.create_index([("role", ASCENDING)])
    db.users.create_index([("created_at", DESCENDING)])

    db.command({
        "collMod": "users",
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["email", "role", "created_at"],
                "properties": {
                    "email": {"bsonType": "string"},
                    "role": {"bsonType": "string"},
                    "created_at": {"bsonType": "date"}
                }
            }
        },
        "validationLevel": "moderate"
    })

    # =========================
    # HOUSES
    # =========================
    db.houses.create_index([("status", ASCENDING)])
    db.houses.create_index([("agent_id", ASCENDING)])
    db.houses.create_index([("created_at", DESCENDING)])
    db.houses.create_index([("location", ASCENDING)])
    db.houses.create_index([("price", ASCENDING)])

    db.command({
        "collMod": "houses",
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["title", "agent_id", "location", "price", "created_at"],
                "properties": {
                    "title": {"bsonType": "string"},
                    "agent_id": {"bsonType": "objectId"},
                    "location": {"bsonType": "string"},
                    "price": {"bsonType": "double"},
                    "status": {"bsonType": "string"},
                    "created_at": {"bsonType": "date"}
                }
            }
        },
        "validationLevel": "moderate"
    })

    # =========================
    # CONTACT REQUESTS
    # =========================
    db.contact_requests.create_index([("haunter_id", ASCENDING)])
    db.contact_requests.create_index([("agent_id", ASCENDING)])
    db.contact_requests.create_index([("house_id", ASCENDING)])
    db.contact_requests.create_index([("created_at", DESCENDING)])

    db.command({
        "collMod": "contact_requests",
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["haunter_id", "agent_id", "house_id", "created_at"],
                "properties": {
                    "haunter_id": {"bsonType": "objectId"},
                    "agent_id": {"bsonType": "objectId"},
                    "house_id": {"bsonType": "objectId"},
                    "status": {"bsonType": "string"},
                    "created_at": {"bsonType": "date"}
                }
            }
        },
        "validationLevel": "moderate"
    })

    # =========================
    # FAVORITES
    # =========================
    db.favorites.create_index([("haunter_id", ASCENDING)])
    db.favorites.create_index([("house_id", ASCENDING)])

    db.command({
        "collMod": "favorites",
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["haunter_id", "house_id", "created_at"],
                "properties": {
                    "haunter_id": {"bsonType": "objectId"},
                    "house_id": {"bsonType": "objectId"},
                    "created_at": {"bsonType": "date"}
                }
            }
        },
        "validationLevel": "moderate"
    })

    # =========================
    # REVIEWS
    # =========================
    db.reviews.create_index([("agent_id", ASCENDING)])
    db.reviews.create_index([("haunter_id", ASCENDING)])
    db.reviews.create_index([("created_at", DESCENDING)])

    db.command({
        "collMod": "reviews",
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["agent_id", "haunter_id", "rating", "created_at"],
                "properties": {
                    "agent_id": {"bsonType": "objectId"},
                    "haunter_id": {"bsonType": "objectId"},
                    "rating": {"bsonType": "int"},
                    "comment": {"bsonType": ["string", "null"]},
                    "is_flagged": {"bsonType": "bool"},
                    "created_at": {"bsonType": "date"}
                }
            }
        },
        "validationLevel": "moderate"
    })

    # =========================
    # WALLET
    # =========================
    db.wallets.create_index([("user_id", ASCENDING)], unique=True)

    db.command({
        "collMod": "wallets",
        "validator": {
            "$jsonSchema": {
                "bsonType": "object",
                "required": ["user_id", "balance", "updated_at"],
                "properties": {
                    "user_id": {"bsonType": "objectId"},
                    "balance": {"bsonType": "double"},
                    "updated_at": {"bsonType": "date"}
                }
            }
        },
        "validationLevel": "moderate"
    })

    print("MongoDB indexes and basic validation rules created successfully!")

# Example usage:
# from app.mongo_setup_with_validation import create_indexes_and_validation
# create_indexes_and_validation()
