import logging
import threading
import time
from pathlib import Path

import zulip

log = logging.getLogger(__name__)

HEARTBEAT_FILE = Path("/tmp/bot_heartbeat")
_INTERVAL = 60  # secondes entre chaque sonde


def start(client: zulip.Client) -> None:
    """Lance en arrière-plan un thread qui vérifie la connexion Zulip
    et met à jour HEARTBEAT_FILE tant que tout va bien."""
    t = threading.Thread(target=_loop, args=(client,), daemon=True, name="healthcheck")
    t.start()
    log.info("Healthcheck démarré (interval=%ds, fichier=%s)", _INTERVAL, HEARTBEAT_FILE)


def _loop(client: zulip.Client) -> None:
    while True:
        try:
            result = client.call_endpoint(url="users/me", method="GET")
            if result.get("result") == "success":
                HEARTBEAT_FILE.touch()
            else:
                log.warning("Healthcheck : réponse inattendue de Zulip : %s", result)
        except Exception:
            log.exception("Healthcheck : erreur lors de la sonde Zulip")
        time.sleep(_INTERVAL)
