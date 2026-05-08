"""
Point d'entrée du bot Nextcloud-Zulip.

Utilise le long-polling de l'API Zulip (event queue) pour recevoir
les messages en temps réel, sans nécessiter d'URL publique exposée.
"""

import logging
from typing import Any

import zulip

from src import config
from src.handlers import commands, interactions

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
log = logging.getLogger(__name__)


def on_event(event: dict[str, Any], client: zulip.Client) -> None:
    """Callback appelé pour chaque événement reçu depuis Zulip."""
    if event.get("type") != "message":
        return

    message = event["message"]

    # Ignore les messages envoyés par le bot lui-même
    if message.get("sender_email") == config.ZULIP_EMAIL:
        return

    content: str = message.get("content", "").strip()
    log.debug("Message reçu de %s : %s", message.get("sender_email"), content[:80])

    # Interactions de zform (clics sur boutons)
    if interactions.is_interaction(message):
        try:
            interactions.handle(message, client)
        except Exception:
            log.exception("Erreur lors du traitement d'une interaction")
        return

    # Commandes /nextcloud …
    if content.lower().startswith(config.COMMAND_PREFIX):
        try:
            commands.handle(message, client)
        except Exception:
            log.exception("Erreur lors du traitement de la commande")


def main() -> None:
    log.info("Démarrage du bot Nextcloud-Zulip sur %s", config.ZULIP_SITE)

    client = zulip.Client(
        email=config.ZULIP_EMAIL,
        api_key=config.ZULIP_API_KEY,
        site=config.ZULIP_SITE,
    )

    # call_on_each_message gère la reconnexion automatiquement
    client.call_on_each_message(lambda msg: on_event({"type": "message", "message": msg}, client))


if __name__ == "__main__":
    main()
