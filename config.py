import os
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(BASE_DIR, ".env"))


def _int(name, default):
    try:
        return int(os.getenv(name, default))
    except (TypeError, ValueError):
        return default


class Config:
    SECRET_KEY               = os.getenv("SECRET_KEY", "change-me-secret")
    JWT_SECRET_KEY           = os.getenv("JWT_SECRET_KEY", "change-me-jwt-secret")
    JWT_ACCESS_TOKEN_EXPIRES = _int("JWT_ACCESS_TOKEN_EXPIRES", 86400)   # seconds

    MYSQL_HOST     = os.getenv("MYSQL_HOST", "localhost")
    MYSQL_USER     = os.getenv("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    MYSQL_DB       = os.getenv("MYSQL_DB", "prahari_db")

    # ── SMS ───────────────────────────────────────────────
    SMS_PROVIDER          = os.getenv("SMS_PROVIDER", "console").strip().lower()
    TWILIO_ACCOUNT_SID    = os.getenv("TWILIO_ACCOUNT_SID", "").strip()
    TWILIO_AUTH_TOKEN     = os.getenv("TWILIO_AUTH_TOKEN", "").strip()
    TWILIO_FROM_NUMBER    = os.getenv("TWILIO_FROM_NUMBER", "").strip()
    NOTIFY_ON_CONTACT_ADD = os.getenv("NOTIFY_ON_CONTACT_ADD", "true").strip().lower() == "true"

    # ── SMTP (email-to-SMS) ───────────────────────────────
    SMTP_HOST        = os.getenv("SMTP_HOST", "smtp.gmail.com").strip()
    SMTP_PORT        = _int("SMTP_PORT", 587)
    SMTP_USER        = os.getenv("SMTP_USER", "").strip()
    SMTP_PASSWORD    = os.getenv("SMTP_PASSWORD", "").strip()
    SMTP_FROM        = os.getenv("SMTP_FROM", "").strip()
    SMTP_SMS_GATEWAY = os.getenv("SMTP_SMS_GATEWAY", "").strip()

    # ── Gemini chatbot ────────────────────────────────────
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "").strip()
    GEMINI_MODEL   = os.getenv("GEMINI_MODEL", "gemini-2.5-flash").strip()
