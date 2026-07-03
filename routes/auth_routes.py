import re
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, set_access_cookies,
    unset_jwt_cookies, jwt_required, get_jwt_identity
)

from models import db, User

auth_bp = Blueprint("auth", __name__)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body harus JSON"}), 400

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()

    # --- Validasi dasar ---
    if not username or not email or not password:
        return jsonify({"error": "username, email, dan password wajib diisi"}), 400

    if len(username) < 3:
        return jsonify({"error": "username minimal 3 karakter"}), 400

    if not EMAIL_REGEX.match(email):
        return jsonify({"error": "Format email tidak valid"}), 400

    if len(password) < 8:
        return jsonify({"error": "password minimal 8 karakter"}), 400

    if User.query.filter_by(username=username).first():
        return jsonify({"error": "Username sudah digunakan"}), 409

    if User.query.filter_by(email=email).first():
        return jsonify({"error": "Email sudah terdaftar"}), 409

    try:
        user = User(username=username, email=email, full_name=full_name)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Gagal membuat user, coba lagi"}), 500

    return jsonify({"message": "Registrasi berhasil", "user": user.to_dict()}), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body harus JSON"}), 400

    identifier = (data.get("username") or data.get("email") or "").strip()
    password = data.get("password") or ""

    if not identifier or not password:
        return jsonify({"error": "username/email dan password wajib diisi"}), 400

    user = User.query.filter(
        (User.username == identifier) | (User.email == identifier.lower())
    ).first()

    if not user or not user.check_password(password):
        return jsonify({"error": "Username/email atau password salah"}), 401

    access_token = create_access_token(identity=user.id)

    response = jsonify({"message": "Login berhasil", "user": user.to_dict()})
    # CRITICAL: token disimpan di HttpOnly cookie, tidak pernah dikirim ke JS/local storage
    set_access_cookies(response, access_token)

    return response, 200


@auth_bp.route("/logout", methods=["POST"])
@jwt_required()
def logout():
    response = jsonify({"message": "Logout berhasil"})
    unset_jwt_cookies(response)
    return response, 200


@auth_bp.route("/me", methods=["GET"])
@jwt_required()
def get_current_user():
    user_id = get_jwt_identity()
    user = User.query.get(user_id)
    if not user:
        return jsonify({"error": "User tidak ditemukan"}), 404
    return jsonify({"user": user.to_dict()}), 200