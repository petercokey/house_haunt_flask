# app/utils/auth_helpers.py
from functools import wraps
from flask import jsonify, g
from flask_login import current_user, login_user
from flask_jwt_extended import verify_jwt_in_request, get_jwt_identity
from app.models import User

def jwt_or_login_required(role=None):
    """
    Accepts either Flask-Login session or valid JWT cookie.
    Optionally restricts by role.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user = None

            # 1️⃣ Try Flask-Login session
            if current_user and current_user.is_authenticated:
                user = current_user
            else:
                # 2️⃣ Try JWT (Flask-JWT-Extended cookie)
                try:
                    verify_jwt_in_request()  # checks cookie automatically
                    identity = get_jwt_identity()
                    if identity:
                        user = User.query.get(identity.get("id"))
                except Exception:
                    return jsonify({"error": "Unauthorized"}), 401

            # 3️⃣ Still no user → reject
            if not user:
                return jsonify({"error": "Unauthorized"}), 401

            # 4️⃣ Optional role restriction
            if role and user.role != role:
                return jsonify({"error": f"Access restricted to {role} users only."}), 403

            # 5️⃣ Sync with Flask-Login for session consistency
            try:
                login_user(user)
            except Exception:
                pass  # avoid double-login crash on Render

            g.user = user
            return f(*args, **kwargs)
        return wrapper
    return decorator
