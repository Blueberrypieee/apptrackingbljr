import os
import logging
from flask import Flask, send_from_directory, jsonify
from config import Config
from database import init_db
from extensions import limiter

# FIX #8: Ganti print() ke logging module yang proper.
# print() tidak bisa dikontrol levelnya dan tidak bisa dikirim ke log aggregator.
# logging bisa dikonfigurasi level, format, dan output destination.
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger(__name__)


def create_app():
    app = Flask(__name__, static_folder="frontend/static")
    app.config.from_object(Config)

    limiter.init_app(app)

    from models.user import User
    from models.progress import Progress
    from models.quiz import QuizSession
    from models.folder import Folder

    init_db(app)

    from routes.auth import auth_bp
    from routes.progress import progress_bp
    from routes.quiz import quiz_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(progress_bp)
    app.register_blueprint(quiz_bp)

    # Security headers
    @app.after_request
    def add_security_headers(response):
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "no-referrer"

        # FIX #9: Tambah Content-Security-Policy header yang sebelumnya tidak ada.
        # Tanpa CSP, XSS attack bisa inject dan jalankan script apapun.
        # Konfigurasi ini:
        #   default-src 'self'         → hanya izinkan resource dari domain sendiri
        #   script-src 'self' unpkg.com → izinkan script dari self + unpkg (untuk lucide)
        #   style-src 'self' 'unsafe-inline' fonts.googleapis.com → izinkan inline CSS + Google Fonts
        #   font-src fonts.gstatic.com → izinkan font dari Google
        #   img-src 'self' data:       → izinkan gambar dari self + base64
        #   connect-src 'self'         → hanya izinkan fetch/XHR ke domain sendiri
        response.headers["Content-Security-Policy"] = (
            "default-src 'self'; "
            "script-src 'self' https://unpkg.com 'unsafe-inline'; "
            "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
            "font-src https://fonts.gstatic.com; "
            "img-src 'self' data:; "
            "connect-src 'self';"
        )
        return response

    @app.errorhandler(404)
    def not_found(e):
        return {"error": "Not found"}, 404

    @app.errorhandler(500)
    def internal_error(e):
        logger.error(f"Internal server error: {e}")
        return {"error": "Internal server error"}, 500

    @app.route("/")
    @app.route("/login")
    @app.route("/dashboard")
    @app.route("/history")
    @app.route("/challenge")
    def serve_frontend(path=None):
        return send_from_directory("frontend", "index.html")

    @app.route("/static/<path:filename>")
    def serve_static(filename):
        return send_from_directory("frontend/static", filename)

    return app


if __name__ == "__main__":
    app = create_app()
    # FIX #8: Pakai logger, bukan print()
    logger.info(f"Belajar Tracker running at http://localhost:{Config.PORT}")
    logger.info(f"AI Provider: {Config.AI_NAME} ({Config.AI_MODEL})")
    app.run(
        host="0.0.0.0",
        port=Config.PORT,
        debug=Config.DEBUG
    )

