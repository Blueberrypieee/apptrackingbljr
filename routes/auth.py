from flask import Blueprint, request, jsonify, session
from models.user import User
from database import db
from extensions import limiter
import os

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

ADMIN_USERNAME = os.getenv("ADMIN_USERNAME", "").strip().lower()


@auth_bp.route("/register", methods=["POST"])
@limiter.limit("5 per minute")
def register():
    data = request.get_json(silent=True) or {}

    # FIX: Paksa username selalu lowercase saat disimpan.
    # Sebelumnya: "abc213" dan "Abc213" dianggap user berbeda di DB,
    # tapi keduanya lolos cek admin karena .lower() — dua orang bisa jadi admin.
    # Sekarang: username di-lowercase dulu sebelum apapun dicek/disimpan.
    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()

    if not username or not password:
        return jsonify({"error": "Username dan password wajib diisi"}), 400

    if len(password) < 6:
        return jsonify({"error": "Password minimal 6 karakter"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username sudah dipakai"}), 409

    is_admin = bool(ADMIN_USERNAME and username == ADMIN_USERNAME)

    user = User(username=username, is_admin=is_admin)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()

    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    return jsonify({"message": "Registrasi berhasil", "user": user.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
@limiter.limit("10 per minute")
def login():
    data = request.get_json(silent=True) or {}

    # FIX: Login juga pakai lowercase agar konsisten dengan data yang disimpan
    username = data.get("username", "").strip().lower()
    password = data.get("password", "").strip()

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"error": "Username atau password salah"}), 401

    session.clear()
    session["user_id"] = user.id
    session["username"] = user.username
    return jsonify({"message": "Login berhasil", "user": user.to_dict()}), 200


@auth_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logout berhasil"}), 200


@auth_bp.route("/me", methods=["GET"])
def me():
    if "user_id" not in session:
        return jsonify({"error": "Belum login"}), 401

    user = db.session.get(User, session["user_id"])

    if not user:
        session.clear()
        return jsonify({"error": "Sesi tidak valid, silakan login ulang"}), 401

    return jsonify({"user": user.to_dict()}), 200

