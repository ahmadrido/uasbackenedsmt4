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

    result = []
    for f in files:
        data = f.to_dict(include_owner=False)
        data["shared_with"] = [
            {"id": s.shared_with.id, "username": s.shared_with.username}
            for s in f.shares if s.shared_with
        ]
        result.append(data)

    return jsonify({"files": result}), 200


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

@file_bp.route("/<file_id>", methods=["GET"])
@jwt_required()
def get_file_detail(file_id):
    """Detail satu file. Jika diakses oleh owner, sertakan daftar user yang di-share."""
    user_id = get_jwt_identity()

    file_item = FileItem.query.get(file_id)
    if not file_item:
        return jsonify({"error": "File tidak ditemukan"}), 404

    is_owner = file_item.owner_id == user_id
    is_shared_with_user = FileShare.query.filter_by(
        file_id=file_item.id, shared_with_id=user_id
    ).first() is not None

    if not (file_item.is_public or is_owner or is_shared_with_user):
        return jsonify({"error": "Anda tidak memiliki akses ke file ini"}), 403

    data = file_item.to_dict()
    if is_owner:
        data["shared_with_ids"] = [s.shared_with_id for s in file_item.shares]

    return jsonify({"file": data}), 200


@file_bp.route("/<file_id>", methods=["PUT", "PATCH"])
@jwt_required()
def update_file(file_id):
    """
    Edit metadata file: title, description, is_public, share_with, dan opsional ganti file fisik.
    Dikirim sebagai multipart/form-data (sama seperti upload) agar bisa menyertakan file baru.
    """
    user_id = get_jwt_identity()

    file_item = FileItem.query.get(file_id)
    if not file_item:
        return jsonify({"error": "File tidak ditemukan"}), 404

    if file_item.owner_id != user_id:
        return jsonify({"error": "Hanya pemilik yang bisa mengedit file ini"}), 403

    form = request.form
    new_file = request.files.get("file")  # opsional, hanya diisi jika user ganti file

    title = form.get("title")
    description = form.get("description")
    is_public_raw = form.get("is_public")
    share_with_provided = "share_with" in form
    share_with_raw = form.get("share_with", "")

    # --- Validasi & update field teks ---
    if title is not None:
        title = title.strip()
        if not title:
            return jsonify({"error": "Judul tidak boleh kosong"}), 400
        file_item.title = title

    if description is not None:
        file_item.description = description.strip()

    if is_public_raw is not None:
        file_item.is_public = str(is_public_raw).lower() == "true"

    # --- Ganti file fisik jika ada upload baru ---
    old_path_to_delete = None
    if new_file and new_file.filename:
        if not _allowed_file(new_file.filename):
            return jsonify({"error": "Tipe file tidak diizinkan"}), 400

        old_path_to_delete = os.path.join(
            current_app.config["UPLOAD_FOLDER"], file_item.stored_filename
        )

        original_filename = secure_filename(new_file.filename)
        ext = original_filename.rsplit(".", 1)[1].lower()
        new_stored_filename = f"{uuid.uuid4().hex}.{ext}"
        new_path = os.path.join(current_app.config["UPLOAD_FOLDER"], new_stored_filename)

        try:
            new_file.save(new_path)
        except Exception:
            return jsonify({"error": "Gagal menyimpan file baru"}), 500

        file_item.original_filename = original_filename
        file_item.stored_filename = new_stored_filename
        file_item.file_size = os.path.getsize(new_path)
        file_item.mime_type = new_file.mimetype

    # --- Update sharing (M2M) ---
    try:
        if file_item.is_public:
            # Jadi publik: hapus semua share spesifik yang ada
            FileShare.query.filter_by(file_id=file_item.id).delete()

        elif share_with_provided:
            # Private & daftar share dikirim ulang: sinkronkan (tambah baru, hapus yang dihilangkan)
            new_ids = {uid.strip() for uid in share_with_raw.split(",") if uid.strip()}
            new_ids.discard(user_id)

            valid_users = User.query.filter(User.id.in_(new_ids)).all() if new_ids else []
            valid_ids = {u.id for u in valid_users}

            existing_shares = {s.shared_with_id: s for s in file_item.shares}

            for uid, share in existing_shares.items():
                if uid not in valid_ids:
                    db.session.delete(share)

            for uid in valid_ids:
                if uid not in existing_shares:
                    db.session.add(FileShare(
                        file_id=file_item.id,
                        shared_with_id=uid,
                        shared_by_id=user_id,
                    ))

        db.session.commit()
    except Exception:
        db.session.rollback()
        return jsonify({"error": "Gagal memperbarui data file"}), 500

    if old_path_to_delete and os.path.exists(old_path_to_delete):
        os.remove(old_path_to_delete)

    return jsonify({"message": "File berhasil diperbarui", "file": file_item.to_dict()}), 200

@file_bp.route("/<file_id>/preview", methods=["GET"])
@jwt_required()
def preview_file(file_id):
    """Serve file inline (bukan attachment) — khusus untuk thumbnail gambar di UI."""
    user_id = get_jwt_identity()

    file_item = FileItem.query.get(file_id)
    if not file_item:
        return jsonify({"error": "File tidak ditemukan"}), 404

    is_owner = file_item.owner_id == user_id
    is_shared_with_user = FileShare.query.filter_by(
        file_id=file_item.id, shared_with_id=user_id
    ).first() is not None

    if not (file_item.is_public or is_owner or is_shared_with_user):
        return jsonify({"error": "Anda tidak memiliki akses ke file ini"}), 403

    if not file_item.mime_type or not file_item.mime_type.startswith("image/"):
        return jsonify({"error": "Preview hanya tersedia untuk file gambar"}), 415

    return send_from_directory(
        current_app.config["UPLOAD_FOLDER"],
        file_item.stored_filename,
        as_attachment=False,
        mimetype=file_item.mime_type
    )