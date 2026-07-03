import os
import uuid
from flask import Blueprint, request, jsonify, send_from_directory, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename

from models import db, User, FileItem, FileShare

file_bp = Blueprint("files", __name__)


def _allowed_file(filename: str) -> bool:
    return (
        "." in filename
        and filename.rsplit(".", 1)[1].lower() in current_app.config["ALLOWED_EXTENSIONS"]
    )


@file_bp.route("/upload", methods=["POST"])
@jwt_required()
def upload_file():
    owner_id = get_jwt_identity()

    if "file" not in request.files:
        return jsonify({"error": "Tidak ada file yang dikirim (field 'file')"}), 400

    uploaded = request.files["file"]
    if uploaded.filename == "":
        return jsonify({"error": "Nama file kosong"}), 400

    if not _allowed_file(uploaded.filename):
        return jsonify({"error": "Tipe file tidak diizinkan"}), 400

    title = (request.form.get("title") or "").strip()
    description = (request.form.get("description") or "").strip()
    is_public = request.form.get("is_public", "false").lower() == "true"

    # share_with: comma-separated user id, hanya relevan jika is_public == False
    share_with_raw = request.form.get("share_with", "")
    share_with_ids = [uid.strip() for uid in share_with_raw.split(",") if uid.strip()]

    if not title:
        title = uploaded.filename

    original_filename = secure_filename(uploaded.filename)
    ext = original_filename.rsplit(".", 1)[1].lower()
    stored_filename = f"{uuid.uuid4().hex}.{ext}"
    save_path = os.path.join(current_app.config["UPLOAD_FOLDER"], stored_filename)

    try:
        uploaded.save(save_path)
        file_size = os.path.getsize(save_path)
    except Exception:
        return jsonify({"error": "Gagal menyimpan file di server"}), 500

    try:
        file_item = FileItem(
            original_filename=original_filename,
            stored_filename=stored_filename,
            title=title,
            description=description,
            file_size=file_size,
            mime_type=uploaded.mimetype,
            is_public=is_public,
            owner_id=owner_id,
        )
        db.session.add(file_item)
        db.session.flush()  # supaya file_item.id tersedia sebelum commit

        created_shares = []
        if not is_public and share_with_ids:
            # Validasi user tujuan share, skip yang tidak valid / diri sendiri
            valid_users = User.query.filter(User.id.in_(share_with_ids)).all()
            valid_user_ids = {u.id for u in valid_users if u.id != owner_id}

            for target_id in valid_user_ids:
                share = FileShare(
                    file_id=file_item.id,
                    shared_with_id=target_id,
                    shared_by_id=owner_id,
                )
                db.session.add(share)
                created_shares.append(target_id)

        db.session.commit()
    except Exception:
        db.session.rollback()
        # Bersihkan file fisik jika DB gagal
        if os.path.exists(save_path):
            os.remove(save_path)
        return jsonify({"error": "Gagal menyimpan metadata file"}), 500

    return jsonify({
        "message": "File berhasil diunggah",
        "file": file_item.to_dict(),
        "shared_with": created_shares
    }), 201


@file_bp.route("/public", methods=["GET"])
@jwt_required()
def get_public_files():
    files = FileItem.query.filter_by(is_public=True).order_by(FileItem.created_at.desc()).all()
    return jsonify({"files": [f.to_dict() for f in files]}), 200


@file_bp.route("/shared-with-me", methods=["GET"])
@jwt_required()
def get_shared_with_me():
    user_id = get_jwt_identity()

    shares = (
        FileShare.query
        .filter_by(shared_with_id=user_id)
        .order_by(FileShare.shared_at.desc())
        .all()
    )

    return jsonify({"shared_files": [s.to_dict() for s in shares]}), 200


@file_bp.route("/my-files", methods=["GET"])
@jwt_required()
def get_my_files():
    user_id = get_jwt_identity()
    files = FileItem.query.filter_by(owner_id=user_id).order_by(FileItem.created_at.desc()).all()
    return jsonify({"files": [f.to_dict(include_owner=False) for f in files]}), 200


@file_bp.route("/<file_id>/download", methods=["GET"])
@jwt_required()
def download_file(file_id):
    user_id = get_jwt_identity()

    file_item = FileItem.query.get(file_id)
    if not file_item:
        return jsonify({"error": "File tidak ditemukan"}), 404

    # --- Authorization check ---
    is_owner = file_item.owner_id == user_id
    is_shared_with_user = FileShare.query.filter_by(
        file_id=file_item.id, shared_with_id=user_id
    ).first() is not None

    if not (file_item.is_public or is_owner or is_shared_with_user):
        return jsonify({"error": "Anda tidak memiliki akses ke file ini"}), 403

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        file_item.stored_filename,
        as_attachment=True,
        download_name=file_item.original_filename
    )


@file_bp.route("/<file_id>", methods=["DELETE"])
@jwt_required()
def delete_file(file_id):
    user_id = get_jwt_identity()

    file_item = FileItem.query.get(file_id)
    if not file_item:
        return jsonify({"error": "File tidak ditemukan"}), 404

    if file_item.owner_id != user_id:
        return jsonify({"error": "Hanya pemilik yang bisa menghapus file ini"}), 403

    file_path = os.path.join(current_app.config["UPLOAD_FOLDER"], file_item.stored_filename)

    try:
        db.session.delete(file_item)  # cascade akan hapus FileShare terkait
        db.session.commit()
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Gagal menghapus file"}), 500

    return jsonify({"message": "File berhasil dihapus"}), 200


@file_bp.route("/users", methods=["GET"])
@jwt_required()
def list_users_for_sharing():
    """Dipakai frontend untuk populate multi-select target share (exclude diri sendiri)."""
    user_id = get_jwt_identity()
    users = User.query.filter(User.id != user_id).order_by(User.username.asc()).all()
    return jsonify({"users": [u.to_dict() for u in users]}), 200