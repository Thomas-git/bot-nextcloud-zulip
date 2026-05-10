import logging
import re
import time
from typing import Any

import zulip

from src import config, healthcheck
from src.handlers import commands, dm_flow

logging.basicConfig(
    level=getattr(logging, config.LOG_LEVEL, logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

# Bibliothèques tierces bavardes : silencieuses sauf en DEBUG
if config.LOG_LEVEL != "DEBUG":
    for _noisy in ("urllib3", "zulip", "requests"):
        logging.getLogger(_noisy).setLevel(logging.WARNING)

_MENTION_RE = re.compile(r"^@\*\*[^*]+\*\*\s*")


def on_event(event: dict[str, Any], client: zulip.Client) -> None:
    if event.get("type") != "message":
        return

    message = event["message"]
    if message.get("sender_email") == config.ZULIP_EMAIL:
        return

    content = _MENTION_RE.sub("", message.get("content", "")).strip()
    message = {**message, "content": content}
    log.debug("Message de %s (%s) : %s",
              message.get("sender_email"), message.get("type"), content[:80])

    if message.get("type") == "private" and dm_flow.has_session(message["sender_email"]):
        try:
            dm_flow.handle(message, client)
        except Exception:
            log.exception("Erreur dm_flow")
        return

    try:
        commands.handle(message, client)
    except Exception:
        log.exception("Erreur commande")


_RECONNECT_DELAY_MIN = 5
_RECONNECT_DELAY_MAX = 300  # 5 minutes


def main() -> None:
    log.info("Démarrage du bot Nextcloud-Zulip sur %s", config.ZULIP_SITE)
    client = zulip.Client(
        email=config.ZULIP_EMAIL,
        api_key=config.ZULIP_API_KEY,
        site=config.ZULIP_SITE,
    )
    healthcheck.start(client)

    delay = _RECONNECT_DELAY_MIN
    while True:
        try:
            log.info("Connexion à Zulip...")
            started_at = time.monotonic()
            client.call_on_each_message(
                lambda msg: on_event({"type": "message", "message": msg}, client)
            )
            # call_on_each_message est censé être bloquant indéfiniment ;
            # s'il retourne sans exception, on reconnecte immédiatement
            delay = _RECONNECT_DELAY_MIN
        except KeyboardInterrupt:
            log.info("Arrêt du bot.")
            break
        except Exception:
            elapsed = time.monotonic() - started_at
            if elapsed > 60:
                # La connexion était stable : on repart vite
                delay = _RECONNECT_DELAY_MIN
            log.exception(
                "Connexion Zulip interrompue (durée %.0fs). Nouvelle tentative dans %ds.",
                elapsed, delay,
            )
            time.sleep(delay)
            delay = min(delay * 2, _RECONNECT_DELAY_MAX)


if __name__ == "__main__":
    main()
