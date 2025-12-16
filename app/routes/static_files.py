# app/routes/static_files.py
from flask import Blueprint, send_from_directory, current_app
import os

bp = Blueprint(
    "static_files",
    __name__,
    url_prefix="/uploads"
)

@bp.route("/<path:filename>")
def serve_upload(filename):
    upload_folder = os.path.join(current_app.root_path, "uploads")
    return send_from_directory(upload_folder, filename)
