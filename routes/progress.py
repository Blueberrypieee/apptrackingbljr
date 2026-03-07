import os
import uuid
from flask import Blueprint, request, jsonify, session, current_app, send_file
from werkzeug.utils import secure_filename
from models.progress import Progress
from models.folder import Folder
from database import db
from datetime import datetime, date

progress_bp = Blueprint("progress", __name__, url_prefix="/api/progress")

def login_required(f):
    from functools import wraps
    @wraps(f)
    def decorated(*args, **kwargs):
        if "user_id" not in session:
            return jsonify({"error": "Belum login"}), 401
        return f(*args, **kwargs)
    return decorated

def allowed_file(filename):
    allowed = current_app.config["ALLOWED_EXTENSIONS"]
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed


# ===== FOLDER ENDPOINTS =====

@progress_bp.route("/folders", methods=["GET"])
@login_required
def get_folders():
    user_id = session["user_id"]
    folders = Folder.query.filter_by(user_id=user_id).order_by(Folder.created_at.desc()).all()
    return jsonify({"folders": [f.to_dict() for f in folders]}), 200


@progress_bp.route("/folders", methods=["POST"])
@login_required
def create_folder():
    user_id = session["user_id"]
    data = request.get_json(silent=True) or {}
    name = data.get("name", "").strip()

    if not name:
        return jsonify({"error": "Nama folder wajib diisi"}), 400

    if Folder.query.filter_by(user_id=user_id, name=name).first():
        return jsonify({"error": "Folder dengan nama ini sudah ada"}), 409

    folder = Folder(user_id=user_id, name=name)
    db.session.add(folder)
    db.session.commit()
    return jsonify({"message": "Folder berhasil dibuat", "folder": folder.to_dict()}), 201


@progress_bp.route("/folders/<int:folder_id>", methods=["DELETE"])
@login_required
def delete_folder(folder_id):
    user_id = session["user_id"]
    folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()

    if not folder:
        return jsonify({"error": "Folder tidak ditemukan"}), 404

    # Progress di dalam folder jadi unfiled (folder_id = null)
    Progress.query.filter_by(folder_id=folder_id, user_id=user_id).update({"folder_id": None})
    db.session.delete(folder)
    db.session.commit()
    return jsonify({"message": "Folder berhasil dihapus"}), 200


@progress_bp.route("/<int:progress_id>/move", methods=["PATCH"])
@login_required
def move_to_folder(progress_id):
    user_id = session["user_id"]
    progress = Progress.query.filter_by(id=progress_id, user_id=user_id).first()

    if not progress:
        return jsonify({"error": "Progress tidak ditemukan"}), 404

    data = request.get_json(silent=True) or {}
    folder_id = data.get("folder_id")  # None = unfiled

    if folder_id:
        folder = Folder.query.filter_by(id=folder_id, user_id=user_id).first()
        if not folder:
            return jsonify({"error": "Folder tidak ditemukan"}), 404

    progress.folder_id = folder_id
    db.session.commit()
    return jsonify({"message": "Progress berhasil dipindahkan", "progress": progress.to_dict()}), 200


# ===== PROGRESS ENDPOINTS =====

@progress_bp.route("/", methods=["GET"])
@login_required
def get_all():
    user_id = session["user_id"]
    date_str = request.args.get("date")
    folder_id = request.args.get("folder_id")

    query = Progress.query.filter_by(user_id=user_id)

    if date_str:
        try:
            filter_date = datetime.strptime(date_str, "%Y-%m-%d").date()
            query = query.filter_by(date=filter_date)
        except ValueError:
            return jsonify({"error": "Format tanggal salah, gunakan YYYY-MM-DD"}), 400

    if folder_id == "unfiled":
        query = query.filter(Progress.folder_id == None)
    elif folder_id:
        query = query.filter_by(folder_id=int(folder_id))

    progresses = query.order_by(Progress.created_at.desc()).all()
    return jsonify({"progresses": [p.to_dict() for p in progresses]}), 200


@progress_bp.route("/", methods=["POST"])
@login_required
def create():
    user_id = session["user_id"]
    title = request.form.get("title", "").strip()
    link = request.form.get("link", "").strip()
    notes = request.form.get("notes", "").strip()
    date_str = request.form.get("date", "")
    folder_id = request.form.get("folder_id")

    if not title:
        return jsonify({"error": "Judul materi wajib diisi"}), 400

    try:
        entry_date = datetime.strptime(date_str, "%Y-%m-%d").date() if date_str else date.today()
    except ValueError:
        entry_date = date.today()

    file_path = None
    file_name = None
    stored_filename = None

    if "file" in request.files:
        file = request.files["file"]
        if file and file.filename and allowed_file(file.filename):
            original_filename = secure_filename(file.filename)
            ext = original_filename.rsplit(".", 1)[1].lower()
            stored_filename = f"{uuid.uuid4().hex}.{ext}"
            upload_folder = current_app.config["UPLOAD_FOLDER"]
            os.makedirs(upload_folder, exist_ok=True)
            full_path = os.path.join(upload_folder, stored_filename)
            file.save(full_path)
            file_path = full_path
            file_name = original_filename

    progress = Progress(
        user_id=user_id,
        folder_id=int(folder_id) if folder_id else None,
        title=title,
        link=link if link else None,
        notes=notes if notes else None,
        file_path=file_path,
        file_name=file_name,
        stored_filename=stored_filename,
        date=entry_date
    )
    db.session.add(progress)
    db.session.commit()

    return jsonify({"message": "Progress berhasil disimpan", "progress": progress.to_dict()}), 201


@progress_bp.route("/<int:progress_id>", methods=["DELETE"])
@login_required
def delete(progress_id):
    user_id = session["user_id"]
    progress = Progress.query.filter_by(id=progress_id, user_id=user_id).first()

    if not progress:
        return jsonify({"error": "Progress tidak ditemukan"}), 404

    if progress.file_path and os.path.exists(progress.file_path):
        os.remove(progress.file_path)

    db.session.delete(progress)
    db.session.commit()
    return jsonify({"message": "Progress berhasil dihapus"}), 200


@progress_bp.route("/<int:progress_id>/file", methods=["GET"])
@login_required
def serve_file(progress_id):
    user_id = session["user_id"]
    progress = Progress.query.filter_by(id=progress_id, user_id=user_id).first()

    if not progress:
        return jsonify({"error": "Progress tidak ditemukan"}), 404

    if not progress.file_path or not os.path.exists(progress.file_path):
        return jsonify({"error": "File tidak ditemukan"}), 404

    return send_file(progress.file_path, as_attachment=False)

