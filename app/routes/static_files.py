from flask import Blueprint, send_from_directory, current_app
import os

bp_static = Blueprint("static_files", __name__)

@bp_static.route("/uploads/house_images/<path:filename>")
def serve_house_image(filename):
    folder = os.path.join(current_app.root_path, "uploads", "house_images")
    return send_from_directory(folder, filename)
