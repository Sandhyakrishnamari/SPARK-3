import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))

# Check if we're in the nested directory structure
if os.path.exists(os.path.join(BASE_DIR, "SPARK-Student-Pathway-Academic-Readiness-Knowledge-Portal-main")):
    BASE_DIR = os.path.join(BASE_DIR, "SPARK-Student-Pathway-Academic-Readiness-Knowledge-Portal-main")


class Config:
    # =========================================================
    # SPARK BASE DIRECTORY
    # =========================================================
    BASE_DIR = BASE_DIR

    # =========================================================
    # FLASK SECRET KEY
    # =========================================================
    SECRET_KEY = os.environ.get(
        "SECRET_KEY",
        "spark-development-secret-key-change-in-prod"
    )

    # =========================================================
    # DATABASE
    # =========================================================
    # Using SQLite for easier local development
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", "5432")
    DB_NAME = os.environ.get("DB_NAME", "mywebsite")
    DB_USER = os.environ.get("DB_USER", "postgres")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")

    # SQLite database path (use /tmp for Vercel)
    if os.environ.get("VERCEL"):
        DB_PATH = "/tmp/spark.db"
    else:
        DB_PATH = os.path.join(BASE_DIR, "spark.db")
    
    DATABASE_URL = os.environ.get(
        "DATABASE_URL",
        f"sqlite:///{DB_PATH}"
    )
    SQLALCHEMY_DATABASE_URI = DATABASE_URL
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # =========================================================
    # DOCUMENT UPLOAD FOLDER (static/uploads)
    # =========================================================
    if os.environ.get("VERCEL"):
        UPLOAD_FOLDER = "/tmp/uploads"
    else:
        UPLOAD_FOLDER = os.path.join(
            BASE_DIR,
            "static",
            "uploads"
        )

    # =========================================================
    # MAXIMUM FILE SIZE (16 MB)
    # =========================================================
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # =========================================================
    # ALLOWED DOCUMENT TYPES
    # =========================================================
    ALLOWED_EXTENSIONS = {
        "pdf",
        "png",
        "jpg",
        "jpeg",
        "doc",
        "docx",
        "txt"
    }