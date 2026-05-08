"""
Routeur de commandes /nextcloud.

Chaque commande reçoit le message Zulip brut et le client Zulip, et renvoie
un dict de réponse (content + widget_content optionnel).
"""

from typing import Any

import zulip

from src import config
from src.nextcloud.client import NextcloudClient
from src.zulip_ui import forms

_nc = NextcloudClient()

USAGE = """\
**Bot Nextcloud — commandes disponibles**

- `/nextcloud recent` — fichiers modifiés ces 7 derniers jours
- `/nextcloud recent <N>` — fichiers des N derniers jours
- `/nextcloud help` — affiche cette aide
"""


def handle(message: dict[str, Any], client: zulip.Client) -> None:
    """Analyse la commande et envoie la réponse appropriée."""
    content: str = message.get("content", "").strip()

    # Retire le préfixe /nextcloud
    if not content.lower().startswith(config.COMMAND_PREFIX):
        return
    args = content[len(config.COMMAND_PREFIX):].strip().split()

    if not args or args[0] == "help":
        _reply(message, client, {"content": USAGE})
        return

    cmd = args[0].lower()
    if cmd == "recent":
        _cmd_recent(message, client, args[1:])
    else:
        _reply(message, client, {"content": f"Commande inconnue : `{cmd}`. Tapez `/nextcloud help`."})


# ── commandes ─────────────────────────────────────────────────────────────────

def _cmd_recent(
    message: dict[str, Any],
    client: zulip.Client,
    args: list[str],
) -> None:
    days = config.RECENT_DAYS
    if args:
        try:
            days = int(args[0])
        except ValueError:
            _reply(message, client, {"content": f"Argument invalide : `{args[0]}` (attendu : nombre de jours)"})
            return

    try:
        files = _nc.recent_files(days=days)
    except Exception as exc:
        _reply(message, client, {"content": f"Erreur Nextcloud : {exc}"})
        return

    response = forms.recent_files_form(files, days)
    _reply(message, client, response)


# ── utilitaire ────────────────────────────────────────────────────────────────

def _reply(
    message: dict[str, Any],
    client: zulip.Client,
    response: dict[str, Any],
) -> None:
    """Envoie une réponse dans le même flux/sujet ou MP."""
    msg_type = message.get("type")

    payload: dict[str, Any] = {
        "type": msg_type,
        "content": response.get("content", ""),
    }

    if response.get("widget_content"):
        payload["widget_content"] = response["widget_content"]

    if msg_type == "stream":
        payload["to"] = message["display_recipient"]
        payload["topic"] = message["subject"]
    else:
        payload["to"] = [message["sender_email"]]

    client.send_message(payload)
