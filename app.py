import os
from flask import Flask, jsonify
from flask_jwt_extended import JWTManager
from flask_cors import CORS

from config import DevelopmentConfig
from models import db
from routes.view_routes import view_bp
from flask_mail import Mail
from dotenv import load_dotenv
from flask import render_template, request, jsonify

load_dotenv()
mail = Mail()

def create_app(config_class=DevelopmentConfig):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Pastikan folder upload ada
    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

    # --- Init extensions ---
    db.init_app(app)

    jwt = JWTManager(app)
    mail.init_app(app)

    # CORS: support_credentials wajib True agar cookie ikut terkirim dari frontend
    CORS(
        app,
        supports_credentials=True,
        origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(",")
    )

    # --- Register blueprints ---
    from routes.auth_routes import auth_bp
    from routes.file_routes import file_bp

    app.register_blueprint(auth_bp, url_prefix="/api/auth")
    app.register_blueprint(file_bp, url_prefix="/api/files")
    app.register_blueprint(view_bp)

    # --- JWT error handlers ---
    @jwt.unauthorized_loader
    def missing_token_callback(reason):
        return jsonify({"error": "Missing or invalid authentication token", "detail": reason}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(reason):
        return jsonify({"error": "Invalid token", "detail": reason}), 422

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has expired"}), 401

    @jwt.revoked_token_loader
    def revoked_token_callback(jwt_header, jwt_payload):
        return jsonify({"error": "Token has been revoked"}), 401

    # --- General error handlers ---
    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Resource not found"}), 404

    @app.errorhandler(404)
    def not_found(e):
        if request.path.startswith('/api'):
            return jsonify({"error": "Resource not found"}), 404
            
        return render_template('404.html'), 404

    @app.errorhandler(413)
    def too_large(e):
        return jsonify({"error": "File too large, maximum size is 10MB"}), 413

    @app.errorhandler(500)
    def server_error(e):
        return jsonify({"error": "Internal server error"}), 500

    with app.app_context():
        db.create_all()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=5000)