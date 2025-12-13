from flask import Blueprint

bp = Blueprint("admin", __name__, url_prefix="/api/admin")

@bp.route("/ping")
def ping():
    return {"message": "admin alive"}