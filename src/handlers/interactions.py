"""
Gestion des interactions avec les zforms (clics sur les boutons).

Quand un utilisateur clique sur un choix dans un zform, Zulip envoie
un nouveau message dans la conversation avec le texte `reply` défini
dans le widget.  Ce handler intercepte ces messages internes.
"""

from typing import Any

import zulip

from src.nextcloud.client import NextcloudClient
from src.zulip_ui import forms

_nc = NextcloudClient()

# Préfixe interne utilisé dans forms.py pour les commandes de liaison
_LINK_PREFIX = "link_file:"


def is_interaction(message: dict[str, Any]) -> bool:
    """Retourne True si le message est une interaction de zform (commande interne)."""
    content: str = message.get("content", "").strip()
    return content.startswith(_LINK_PREFIX)


def handle(message: dict[str, Any], client: zulip.Client) -> None:
    """Traite un clic de zform : poste le lien Nextcloud dans la conversation."""
    content: str = message.get("content", "").strip()
    path = content[len(_LINK_PREFIX):]

    file_info = _nc.file_info(path)
    if file_info is None:
        _reply(message, client, f"Fichier introuvable : `{path}`")
        return

    _reply(message, client, forms.file_link_message(file_info))


# ── utilitaire ────────────────────────────────────────────────────────────────

def _reply(message: dict[str, Any], client: zulip.Client, content: str) -> None:
    msg_type = message.get("type")
    payload: dict[str, Any] = {"type": msg_type, "content": content}

    if msg_type == "stream":
        payload["to"] = message["display_recipient"]
        payload["topic"] = message["subject"]
    else:
        payload["to"] = [message["sender_email"]]

    client.send_message(payload)
