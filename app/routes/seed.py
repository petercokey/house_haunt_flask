# app/routes/seed.py
from flask import Blueprint, jsonify, request, current_app
from werkzeug.security import generate_password_hash
from bson import ObjectId
import os
from datetime import datetime

bp = Blueprint("seed", __name__, url_prefix="/api/seed")

# Set this in Render environment variables
SECRET_SEED_KEY = os.getenv("SEED_KEY", "mydevkey123")

@bp.route("/test-mongo")
def test_mongo():
    mongo = current_app.mongo
    mongo.db.test.insert_one({"msg": "Hello Mongo!", "created_at": datetime.utcnow()})
    count = mongo.db.test.count_documents({})
    return jsonify({"message": "✅ Connected successfully!", "total_docs": count}), 200


@bp.route("/", methods=["POST"])
def seed_data():
    """Seed dummy data into MongoDB (protected by secret key)."""
    key = request.args.get("key")
    if key != SECRET_SEED_KEY:
        return jsonify({"error": "Unauthorized access"}), 403

    mongo = current_app.mongo

    try:
        # Clean collections (optional)
        mongo.db.users.delete_many({})
        mongo.db.houses.delete_many({})
        mongo.db.reviews.delete_many({})
        mongo.db.wallets.delete_many({})

        # Create users
        user1 = {
            "_id": ObjectId(),
            "username": "John Doe",
            "email": "john@example.com",
            "password": generate_password_hash("password123"),
            "role": "haunter",
            "created_at": datetime.utcnow()
        }

        user2 = {
            "_id": ObjectId(),
            "username": "Agent Smith",
            "email": "agent@example.com",
            "password": generate_password_hash("password123"),
            "role": "agent",
            "created_at": datetime.utcnow()
        }

        mongo.db.users.insert_many([user1, user2])

        # Create houses
        house1 = {
            "_id": ObjectId(),
            "title": "Cozy Apartment in Lagos",
            "description": "Nice 2-bedroom apartment in Ikeja",
            "location": "Ikeja",
            "price": 150000,
            "agent_id": user2["_id"],
            "created_at": datetime.utcnow()
        }

        house2 = {
            "_id": ObjectId(),
            "title": "Beachside Villa",
            "description": "Luxury villa with ocean view",
            "location": "Lekki",
            "price": 500000,
            "agent_id": user2["_id"],
            "created_at": datetime.utcnow()
        }

        mongo.db.houses.insert_many([house1, house2])

        # Create review
        review1 = {
            "_id": ObjectId(),
            "haunter_id": user1["_id"],
            "agent_id": user2["_id"],
            "rating": 4,
            "comment": "Nice place!",
            "created_at": datetime.utcnow()
        }

        mongo.db.reviews.insert_one(review1)

        # Create wallets
        mongo.db.wallets.insert_many([
            {"user_id": user1["_id"], "balance": 0, "credits_spent": 0, "updated_at": datetime.utcnow()},
            {"user_id": user2["_id"], "balance": 0, "credits_spent": 0, "updated_at": datetime.utcnow()}
        ])

        return jsonify({"message": "✅ Dummy data seeded successfully!"}), 201

    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500
