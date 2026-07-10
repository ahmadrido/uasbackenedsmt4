import re
from flask import Blueprint, request, jsonify, current_app
from flask_jwt_extended import (
    create_access_token, set_access_cookies,
    unset_jwt_cookies, jwt_required, get_jwt_identity
)
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature

from models import db, User
from app import mail

auth_bp = Blueprint("auth", __name__)

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


# =========================================================
# Helper: token reset password
# =========================================================
def _get_serializer():
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"])


def generate_reset_token(email: str) -> str:
    serializer = _get_serializer()
    return serializer.dumps(email, salt=current_app.config["PASSWORD_RESET_SALT"])


def verify_reset_token(token: str, max_age: int = None):
    serializer = _get_serializer()
    max_age = max_age or current_app.config["PASSWORD_RESET_MAX_AGE"]
    return serializer.loads(
        token,
        salt=current_app.config["PASSWORD_RESET_SALT"],
        max_age=max_age
    )


def send_reset_email(user: User, token: str) -> None:
    reset_link = f"{current_app.config['FRONTEND_URL']}/reset-password?token={token}"

    msg = Message(
        subject="Reset Password — SecureDrop Lab",
        recipients=[user.email],
        body=(
            f"Halo {user.username},\n\n"
            f"Kami menerima permintaan reset password untuk akun Anda.\n"
            f"Klik link berikut untuk membuat password baru (berlaku 1 jam):\n\n"
            f"{reset_link}\n\n"
            f"Jika Anda tidak meminta ini, abaikan email ini.\n\n"
            f"— SecureDrop Lab"
        ),
        html=f"""
            <p>Halo <b>{user.username}</b>,</p>
            <p>Kami menerima permintaan reset password untuk akun Anda.</p>
            <p><a href="{reset_link}" style="background:#3B82F6;color:#fff;padding:10px 18px;
               border-radius:8px;text-decoration:none;display:inline-block;">
               Reset Password</a></p>
            <p style="color:#888;font-size:12px;">Link berlaku selama 1 jam. Jika Anda tidak meminta ini, abaikan email ini.</p>
        """
    )
    mail.send(msg)


# =========================================================
# Register / Login / Logout / Me
# =========================================================
@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body harus JSON"}), 400

    username = (data.get("username") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""
    full_name = (data.get("full_name") or "").strip()

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


# =========================================================
# Forgot Password / Reset Password
# =========================================================
@auth_bp.route("/forgot-password", methods=["POST"])
def forgot_password():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body harus JSON"}), 400

    email = (data.get("email") or "").strip().lower()

    if not email:
        return jsonify({"error": "Email wajib diisi"}), 400

    if not EMAIL_REGEX.match(email):
        return jsonify({"error": "Format email tidak valid"}), 400

    # CRITICAL: validasi email harus sudah terdaftar
    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Email tidak terdaftar di sistem kami"}), 404

    token = generate_reset_token(user.email)

    try:
        send_reset_email(user, token)
    except Exception:
        current_app.logger.exception("Gagal mengirim email reset password")
        return jsonify({"error": "Gagal mengirim email, coba lagi nanti"}), 500

    return jsonify({
        "message": "Link reset password telah dikirim ke email Anda. Silakan cek inbox (atau folder spam)."
    }), 200


@auth_bp.route("/verify-reset-token", methods=["POST"])
def verify_reset_token_route():
    """Dipakai frontend untuk cek validitas token sebelum menampilkan form reset."""
    data = request.get_json(silent=True)
    token = data.get("token") if data else None

    if not token:
        return jsonify({"error": "Token tidak ditemukan"}), 400

    try:
        email = verify_reset_token(token)
    except SignatureExpired:
        return jsonify({"error": "Link reset password sudah kedaluwarsa"}), 400
    except BadSignature:
        return jsonify({"error": "Link reset password tidak valid"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Akun terkait tidak ditemukan"}), 404

    return jsonify({"valid": True, "email": email}), 200


@auth_bp.route("/reset-password", methods=["POST"])
def reset_password():
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "Request body harus JSON"}), 400

    token = data.get("token")
    new_password = data.get("new_password") or ""

    if not token:
        return jsonify({"error": "Token tidak ditemukan"}), 400

    if len(new_password) < 8:
        return jsonify({"error": "Password baru minimal 8 karakter"}), 400

    try:
        email = verify_reset_token(token)
    except SignatureExpired:
        return jsonify({"error": "Link reset password sudah kedaluwarsa, silakan minta ulang"}), 400
    except BadSignature:
        return jsonify({"error": "Link reset password tidak valid"}), 400

    user = User.query.filter_by(email=email).first()
    if not user:
        return jsonify({"error": "Akun terkait tidak ditemukan"}), 404

    try:
        user.set_password(new_password)
        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Gagal memperbarui password, coba lagi"}), 500

    return jsonify({"message": "Password berhasil diperbarui. Silakan login dengan password baru."}), 200