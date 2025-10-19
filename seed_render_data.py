import os
from app import create_app, db
from app.models import User, House, Review
from werkzeug.security import generate_password_hash

# ✅ Use Render database, not local (include sslmode=require)
os.environ["DATABASE_URL"] = (
    "postgresql://househaunt_db_user:wsbOZGiJNwl1oqqStbgRgp147IcB6i6o@"
    "dpg-d3khqmt6ubrc73e05ihg-a.ohio-postgres.render.com/househaunt_db?sslmode=require"
)

app = create_app()

with app.app_context():
    print("🚀 Connecting to Render database...")

    db.drop_all()
    db.create_all()
    # === Create Users ===
    agent1 = User(
        username="Jane Realtor",
        email="jane@agency.com",
        password=generate_password_hash("password123"),
        role="agent"
    )
    agent2 = User(
        username="Mike Homes",
        email="mike@realestate.com",
        password=generate_password_hash("password123"),
        role="agent"
    )
    haunter1 = User(
        username="John Doe",
        email="john@haunter.com",
        password=generate_password_hash("password123"),
        role="haunter"
    )
    haunter2 = User(
        username="Emily Walker",
        email="emily@haunter.com",
        password=generate_password_hash("password123"),
        role="haunter"
    )

    db.session.add_all([agent1, agent2, haunter1, haunter2])
    db.session.commit()

    # === Create Houses ===
    house1 = House(
        agent_id=agent1.id,
        title="Luxury Villa in Lekki",
        price=250000000,
        location="Lekki Phase 1, Lagos",
        description="A modern 5-bedroom villa with pool and garden.",
        image_url="https://picsum.photos/400/300?random=1"
    )
    house2 = House(
        agent_id=agent2.id,
        title="Cozy Apartment in Ikeja",
        price=80000000,
        location="Ikeja GRA, Lagos",
        description="2-bedroom apartment near Ikeja City Mall.",
        image_url="https://picsum.photos/400/300?random=2"
    )

    db.session.add_all([house1, house2])
    db.session.commit()

    # === Create Reviews ===
    review1 = Review(
        agent_id=agent1.id,
        haunter_id=haunter1.id,
        rating=4.5,
        comment="Jane was very professional and helpful!"
    )
    review2 = Review(
        agent_id=agent2.id,
        haunter_id=haunter2.id,
        rating=5.0,
        comment="Mike found me the perfect apartment. Highly recommend!"
    )

    db.session.add_all([review1, review2])
    db.session.commit()

    print("✅ Dummy data successfully added to Render database!")
