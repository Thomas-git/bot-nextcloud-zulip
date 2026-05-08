import logging
import re
from typing import Any

import zulip

from src import config
from src.handlers import commands, dm_flow

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)

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

    # DM : si une session est active pour cet utilisateur, on la traite en priorité
    if message.get("type") == "private" and dm_flow.has_session(message["sender_email"]):
        try:
            dm_flow.handle(message, client)
        except Exception:
            log.exception("Erreur dm_flow")
        return

    # Tout le reste → commandes
    try:
        commands.handle(message, client)
    except Exception:
        log.exception("Erreur commande")


def main() -> None:
    log.info("Démarrage du bot Nextcloud-Zulip sur %s", config.ZULIP_SITE)
    client = zulip.Client(
        email=config.ZULIP_EMAIL,
        api_key=config.ZULIP_API_KEY,
        site=config.ZULIP_SITE,
    )
    client.call_on_each_message(
        lambda msg: on_event({"type": "message", "message": msg}, client)
    )


if __name__ == "__main__":
    main()
