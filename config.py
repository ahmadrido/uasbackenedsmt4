import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()

basedir = os.path.abspath(os.path.dirname(__file__))


class Config:
    # --- General ---
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-in-production")

    # --- Database ---
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        "DATABASE_URI", f"sqlite:///{os.path.join(basedir, 'app.db')}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # --- Upload ---
    UPLOAD_FOLDER = os.path.join(basedir, "uploads")
    MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB
    ALLOWED_EXTENSIONS = {
        "pdf", "doc", "docx", "ppt", "pptx", "xls", "xlsx",
        "png", "jpg", "jpeg", "zip", "rar", "txt"
    }

    # --- JWT ---
    JWT_SECRET_KEY = os.environ.get("JWT_SECRET_KEY", "dev-jwt-secret-change-in-production")
    JWT_TOKEN_LOCATION = ["cookies"]
    JWT_ACCESS_COOKIE_NAME = "access_token_cookie"
    JWT_COOKIE_SECURE = os.environ.get("JWT_COOKIE_SECURE", "False") == "True"  # True di production (HTTPS)
    JWT_COOKIE_CSRF_PROTECT = True
    JWT_ACCESS_CSRF_COOKIE_NAME = "csrf_access_token"
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)
    JWT_COOKIE_SAMESITE = "Lax"

    # --- Email (untuk fitur reset password) ---
    MAIL_FROM_NAME = os.environ.get("MAIL_FROM_NAME", "Mail")
    MAIL_SERVER = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    MAIL_PORT = int(os.environ.get("MAIL_PORT", 465))
    MAIL_USE_TLS = os.environ.get("MAIL_USE_TLS", "False") == "True"
    MAIL_USE_SSL = os.environ.get("MAIL_USE_SSL", "False") == "True"
    MAIL_USERNAME = os.environ.get("MAIL_USERNAME")
    MAIL_PASSWORD = os.environ.get("MAIL_PASSWORD")
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)
    MAIL_DEFAULT_SENDER = os.environ.get("MAIL_DEFAULT_SENDER", MAIL_USERNAME)

    # --- Password Reset ---
    FRONTEND_URL = os.environ.get("FRONTEND_URL", "http://localhost:5000")
    PASSWORD_RESET_MAX_AGE = 3600  # 1 jam (dalam detik)
    PASSWORD_RESET_SALT = "password-reset-salt"


class DevelopmentConfig(Config):
    DEBUG = True


class ProductionConfig(Config):
    DEBUG = False
    JWT_COOKIE_SECURE = True

