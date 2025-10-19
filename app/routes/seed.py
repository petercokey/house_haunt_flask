# app/routes/seed.py
from flask import Blueprint, jsonify, request
from app.models import db, User, House, Review
from werkzeug.security import generate_password_hash
import os

bp = Blueprint("seed", __name__, url_prefix="/api/seed")

# Set this in Render environment variables
SECRET_SEED_KEY = os.getenv("SEED_KEY", "mydevkey123")

@bp.route("/", methods=["POST"])
def seed_data():
    """Seed dummy data into Render DB (protected by a secret key)."""
    key = request.args.get("key")

    if key != SECRET_SEED_KEY:
        return jsonify({"error": "Unauthorized access"}), 403

    try:
        db.drop_all()
        db.create_all()

        user1 = User(
            username="John Doe",
            email="john@example.com",
            password=generate_password_hash("password123"),
            role="haunter"
        )
        user2 = User(
            username="Agent Smith",
            email="agent@example.com",
            password=generate_password_hash("password123"),
            role="agent"
        )

        db.session.add_all([user1, user2])
        db.session.commit()

        house1 = House(
            title="Cozy Apartment in Lagos",
            description="Nice 2-bedroom apartment in Ikeja",
            location="Ikeja",
            price=150000,
            agent_id=user2.id   # ✅ make sure to use agent_id not owner_id
        )

        house2 = House(
            title="Beachside Villa",
            description="Luxury villa with ocean view",
            location="Lekki",
            price=500000,
            agent_id=user2.id
        )

        db.session.add_all([house1, house2])
        db.session.commit()

        review1 = Review(
            haunter_id=user1.id,
            agent_id=user2.id,
            rating=4,
            comment="Nice place!"
        )

        db.session.add(review1)
        db.session.commit()

        return jsonify({"message": "✅ Dummy data seeded successfully!"}), 201

    except Exception as e:
        import traceback
        print("❌ ERROR seeding data:", e)
        traceback.print_exc()   # 👈 this line prints the full error to Render logs
        return jsonify({"error": str(e)}), 500
