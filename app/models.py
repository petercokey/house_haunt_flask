from app.extensions import db
from datetime import datetime
from flask_login import UserMixin


# ==========================================================
# 🔹 USER MODEL
# ==========================================================
class User(UserMixin, db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), default="haunter")  # haunter / agent / admin
    credits = db.Column(db.Integer, default=0)
    kyc_verified = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    kyc_document = db.Column(db.String(255))
    is_admin = db.Column(db.Boolean, default=False)

    # Relationship: Agent owns many houses
    houses = db.relationship("House", backref="agent", lazy=True)

    # ✅ FIXED: Explicit, unambiguous relationships to Review
    reviews_written = db.relationship(
        "Review",
        foreign_keys=[lambda: Review.haunter_id],
        backref="haunter",
        lazy=True
    )

    reviews_received = db.relationship(
        "Review",
        foreign_keys=[lambda: Review.agent_id],
        backref="agent",
        lazy=True
    )


# ==========================================================
# 🔹 HOUSE MODEL
# ==========================================================
class House(db.Model):
    __tablename__ = "house"

    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    title = db.Column(db.String(120), nullable=False)
    price = db.Column(db.Float, nullable=False)
    location = db.Column(db.String(120), nullable=False)
    description = db.Column(db.Text)
    image_url = db.Column(db.String(255))
    image_path = db.Column(db.String(255))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ==========================================================
# 🔹 CONTACT REQUEST MODEL
# ==========================================================
class ContactRequest(db.Model):
    __tablename__ = "contact_request"

    id = db.Column(db.Integer, primary_key=True)
    haunter_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    agent_id = db.Column(db.Integer, db.ForeignKey("user.id"))
    house_id = db.Column(db.Integer, db.ForeignKey("house.id"))
    status = db.Column(db.String(20), default="pending")
    credits_deducted = db.Column(db.Integer, default=2)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<ContactRequest Haunter={self.haunter_id} Agent={self.agent_id} -{self.credits_deducted}cr>"


# ==========================================================
# 🔹 FAVORITE MODEL
# ==========================================================
class Favorite(db.Model):
    __tablename__ = "favorites"

    id = db.Column(db.Integer, primary_key=True)
    haunter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    house_id = db.Column(db.Integer, db.ForeignKey("house.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    haunter = db.relationship("User", backref="favorites", lazy=True)
    house = db.relationship("House", backref="favorited_by", lazy=True)

    def __repr__(self):
        return f"<Favorite Haunter={self.haunter_id} House={self.house_id}>"


# ==========================================================
# 🔹 PURCHASE CREDIT MODEL
# ==========================================================
class PurchaseCredit(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    haunter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    amount = db.Column(db.Integer, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __repr__(self):
        return f"<PurchaseCredit {self.haunter_id} +{self.amount}>"


# ==========================================================
# 🔹 REVIEW MODEL
# ==========================================================
class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    agent_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    haunter_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    rating = db.Column(db.Float, nullable=False)
    comment = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    is_flagged = db.Column(db.Boolean, default=False)

    def __repr__(self):
        return f"<Review {self.id} Agent={self.agent_id} Haunter={self.haunter_id}>"


# ==========================================================
# 🔹 KYC MODEL
# ===============================