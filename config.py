import os
import secrets
from dotenv import load_dotenv

load_dotenv()

DEBUG = os.getenv("DEBUG", "False") == "True"

SECRET_KEY = os.getenv("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        # FIX #6: Sebelumnya pakai secrets.token_hex(32) yang generate ulang tiap restart.
        # Akibatnya semua session user invalid setiap app di-restart saat development.
        # Sekarang pakai nilai statis untuk dev — aman karena hanya aktif saat DEBUG=True.
        # JANGAN pakai nilai ini di production. Di production wajib set SECRET_KEY di .env
        SECRET_KEY = "dev-only-secret-key-change-in-production-do-not-use-in-prod"
    else:
        raise RuntimeError("SECRET_KEY tidak di-set. Wajib set SECRET_KEY di .env untuk production.")

class Config:
    SECRET_KEY = SECRET_KEY
    DEBUG = DEBUG
    PORT = int(os.getenv("PORT", 5000))

    # Database
    SQLALCHEMY_DATABASE_URI = os.getenv(
        "DATABASE_URL",
        "sqlite:///belajar_tracker.db"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # Session security
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"

    # FIX #7: SESSION_COOKIE_SECURE sebelumnya default False — berbahaya di production.
    # Cookie session bisa dikirim via HTTP biasa → rentan Man-in-the-Middle.
    # Sekarang: otomatis True kalau bukan DEBUG mode (production).
    # Di development (DEBUG=True) boleh False karena pakai localhost tanpa HTTPS.
    SESSION_COOKIE_SECURE = not DEBUG

    # Upload
    UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max upload
    ALLOWED_EXTENSIONS = {"pdf", "docx", "doc", "txt", "md"}

    # AI Config — edit di .env aja
    AI_NAME = os.getenv("AI_NAME", "Gemini")
    AI_API_KEY = os.getenv("AI_API_KEY", "")
    AI_MODEL = os.getenv("AI_MODEL", "gemini-1.5-flash")
    AI_PROVIDER = os.getenv("AI_PROVIDER", "gemini")

