import uuid
from datetime import datetime, timezone

from models import db


class FileItem(db.Model):
    __tablename__ = "file_items"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    original_filename = db.Column(db.String(255), nullable=False)
    stored_filename = db.Column(db.String(255), nullable=False, unique=True)  # UUID-based name di disk
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text, nullable=True)

    file_size = db.Column(db.Integer, nullable=True)  # bytes
    mime_type = db.Column(db.String(100), nullable=True)

    is_public = db.Column(db.Boolean, default=False, nullable=False)

    owner_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # --- Relasi ---
    owner = db.relationship("User", back_populates="files", foreign_keys=[owner_id])

    shares = db.relationship(
        "FileShare", back_populates="file",
        cascade="all, delete-orphan"
    )

    def to_dict(self, include_owner: bool = True) -> dict:
        data = {
            "id": self.id,
            "original_filename": self.original_filename,
            "title": self.title,
            "description": self.description,
            "file_size": self.file_size,
            "mime_type": self.mime_type,
            "is_public": self.is_public,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
        if include_owner and self.owner:
            data["owner"] = {"id": self.owner.id, "username": self.owner.username}
        return data

    def __repr__(self):
        return f"<FileItem {self.title} ({self.stored_filename})>"