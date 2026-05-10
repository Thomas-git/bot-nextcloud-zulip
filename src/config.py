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

RECENT_DAYS = int(os.getenv("RECENT_DAYS", "7"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()

# Canaux autorisés à invoquer le bot (liste séparée par virgules).
# Si vide, tous les canaux sont acceptés.
_streams_raw = os.getenv("AUTHORIZED_STREAMS", "")
AUTHORIZED_STREAMS: list[str] = [s.strip() for s in _streams_raw.split(",") if s.strip()]

# Mettre à "false" pour désactiver la suppression du message déclencheur.
ALLOW_MESSAGE_DELETE = os.getenv("ALLOW_MESSAGE_DELETE", "true").lower() == "true"
