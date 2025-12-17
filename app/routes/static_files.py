from flask import Blueprint, send_from_directory, current_app

bp = Blueprint("static_files", __name__, url_prefix="/api/files")


@bp.route("/uploads/<path:filename>")
def serve_uploads(filename):
    upload_root = current_app.root_path + "/static/uploads"
    return send_from_directory(upload_root, filename)
