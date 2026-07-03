from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

# Import semua model agar terdaftar ke SQLAlchemy metadata
from models.user import User
from models.file_item import FileItem
from models.file_share import FileShare

__all__ = ["db", "User", "FileItem", "FileShare"]