import uuid
from datetime import datetime, timezone

from models import db


class FileShare(db.Model):
    """Tabel asosiasi many-to-many: File dibagikan ke User tertentu."""
    __tablename__ = "file_shares"
    __table_args__ = (
        db.UniqueConstraint("file_id", "shared_with_id", name="uq_file_shared_with"),
    )

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    file_id = db.Column(db.String(36), db.ForeignKey("file_items.id"), nullable=False)
    shared_with_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)
    shared_by_id = db.Column(db.String(36), db.ForeignKey("users.id"), nullable=False)

    shared_at = db.Column(db.DateTime, default=lambda: datetime.now(timezone.utc))

    # --- Relasi ---
    file = db.relationship("FileItem", back_populates="shares")
    shared_with = db.relationship("User", foreign_keys=[shared_with_id])
    shared_by = db.relationship("User", foreign_keys=[shared_by_id])

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "file": self.file.to_dict(include_owner=False) if self.file else None,
            "shared_with": {"id": self.shared_with.id, "username": self.shared_with.username}
            if self.shared_with else None,
            "shared_by": {"id": self.shared_by.id, "username": self.shared_by.username}
            if self.shared_by else None,
            "shared_at": self.shared_at.isoformat() if self.shared_at else None,
        }

    def __repr__(self):
        return f"<FileShare file={self.file_id} -> user={self.shared_with_id}>"