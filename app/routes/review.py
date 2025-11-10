from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from app.utils.decorators import role_required
 Review, ContactRequest, User
from app.utils.notify import create_notification




bp = Blueprint("review", __name__, url_prefix="/api/review")
@bp.route("/ping")
def ping():
    return jsonify({"message": "review blueprint active!"}), 200

# Create a new review
@bp.route("/create", methods=["POST"])
@role_required("haunter")
def create_review():
    data = request.get_json()
    agent_id = data.get("agent_id")
    rating = data.get("rating")
    comment = data.get("comment", "")

    if not agent_id or not rating:
        return jsonify({"error": "Missing required fields"}), 400

    # Verify haunter has interacted with the agent
    valid_request = ContactRequest.query.filter_by(
        haunter_id=current_user.id,
        agent_id=agent_id,
        status="accepted"
    ).first()

    if not valid_request:
        return jsonify({"error": "You can only review agents youâ€™ve contacted"}), 403

    review = Review(
        haunter_id=current_user.id,
        agent_id=agent_id,
        rating=rating,
        comment=comment
    )
    db.session.add(review)
    db.session.commit()
    create_notification(agent_id, f"You received a new review from {current_user.username} â­")


    return jsonify({
        "message": "Review submitted successfully",
        "review": {
            "id": review.id,
            "rating": review.rating,
            "comment": review.comment
        }
    }), 201


# Get all reviews for a specific agent
@bp.route("/agent/<int:agent_id>", methods=["GET"])
def get_reviews(agent_id):
    agent = User.query.get(agent_id)
    if not agent or agent.role != "agent":
        return jsonify({"error": "Agent not found"}), 404

    reviews = Review.query.filter_by(agent_id=agent_id).all()

    return jsonify({
        "agent_id": agent_id,
        "average_rating": round(sum(r.rating for r in reviews) / len(reviews), 2) if reviews else 0,
        "total_reviews": len(reviews),
        "reviews": [
            {
                "haunter_id": r.haunter_id,
                "rating": r.rating,
                "comment": r.comment,
                "date": r.created_at.strftime("%Y-%m-%d %H:%M")
            }
            for r in reviews
        ]
    }), 200



@bp.route("/flag/<int:review_id>", methods=["PATCH"])
@login_required
@role_required("admin")
def flag_review(review_id):
    review = Review.query.get(review_id)
    if not review:
        return jsonify({"error": "Review not found"}), 404

    review.is_flagged = not review.is_flagged  # toggle
    db.session.commit()

    status = "flagged" if review.is_flagged else "unflagged"
    return jsonify({"message": f"Review {status} successfully"}), 200
