import os
from dotenv import load_dotenv

load_dotenv()


def _require(key: str) -> str:
    value = os.getenv(key)
    if not value:
        raise RuntimeError(f"Variable d'environnement manquante : {key}")
    return value


ZULIP_EMAIL = _require("ZULIP_EMAIL")
ZULIP_API_KEY = _require("ZULIP_API_KEY")
ZULIP_SITE = _require("ZULIP_SITE")

NEXTCLOUD_URL = _require("NEXTCLOUD_URL").rstrip("/")
NEXTCLOUD_USER = _require("NEXTCLOUD_USER")
NEXTCLOUD_PASSWORD = _require("NEXTCLOUD_PASSWORD")

WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = int(os.getenv("WEBHOOK_PORT", "5000"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "")

RECENT_DAYS = int(os.getenv("RECENT_DAYS", "7"))
