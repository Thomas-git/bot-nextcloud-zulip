"""
Routeur de commandes du bot Nextcloud-Zulip.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

import zulip

from src import config
from src.nextcloud.client import NextcloudClient
from src.zulip_ui import forms

log = logging.getLogger(__name__)
_nc = NextcloudClient()

USAGE = """\
**Bot Nextcloud — commandes disponibles**

- `recent` — fichiers modifiés ces 7 derniers jours
- `recent <N>` — fichiers des N derniers jours
- `recent <durée>` — ex : `recent une semaine`, `recent 2 mois`, `recent hier`
- `help` — affiche cette aide
"""


def handle(message: dict[str, Any], client: zulip.Client) -> None:
    content: str = message.get("content", "").strip()
    args = content.split()

    if not args or args[0].lower() == "help":
        _reply(message, client, {"content": USAGE})
        return

    cmd = args[0].lower()
    if cmd == "recent":
        _cmd_recent(message, client, args[1:])
    else:
        _reply(message, client, {"content": f"Commande inconnue : `{cmd}`. Tapez `help`."})


# ── commandes ─────────────────────────────────────────────────────────────────

def _cmd_recent(
    message: dict[str, Any],
    client: zulip.Client,
    args: list[str],
) -> None:
    days = config.RECENT_DAYS
    if args:
        days = _parse_days(" ".join(args))
        if days is None:
            _reply(message, client, {"content": f"Argument non reconnu. Essayez `recent 7`, `recent une semaine`, `recent 2 mois`."})
            return

    try:
        files = _nc.recent_files(days=days)
    except Exception as exc:
        log.exception("Erreur Nextcloud")
        _reply(message, client, {"content": f"Erreur Nextcloud : {exc}"})
        return

    is_dm = message.get("type") == "private"
    if is_dm:
        # Les widgets zform ne sont pas rendus dans les DMs — fallback texte
        response = {"content": forms.recent_files_text(files, days)}
    else:
        response = forms.recent_files_form(files, days)

    _reply(message, client, response)


# ── parsing de durée ─────────────────────────────────────────────────────────

def _parse_days(text: str) -> int | None:
    """Parse un nombre de jours depuis un entier ou une expression naturelle."""
    text = text.strip().lower()

    # entier brut : "14"
    try:
        return max(1, int(text))
    except ValueError:
        pass

    # essaie dateparser si disponible
    try:
        import dateparser  # noqa: PLC0415
        now = datetime.now(timezone.utc)
        parsed = dateparser.parse(
            text,
            languages=["fr", "en"],
            settings={"PREFER_DAY_OF_MONTH": "first", "RELATIVE_BASE": now},
        )
        if parsed:
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            delta = now - parsed
            return max(1, delta.days)
    except ImportError:
        pass

    # fallback manuel pour les cas courants sans dateparser
    _WORDS = {
        "jour": 1, "day": 1,
        "semaine": 7, "week": 7,
        "mois": 30, "month": 30,
        "an": 365, "année": 365, "year": 365,
    }
    tokens = text.replace("-", " ").split()
    for i, token in enumerate(tokens):
        for unit, factor in _WORDS.items():
            if token.startswith(unit):
                # cherche un nombre avant le mot
                n = _word_to_int(tokens[i - 1]) if i > 0 else 1
                return max(1, n * factor)

    return None


_FR_NUMBERS = {
    "un": 1, "une": 1, "deux": 2, "trois": 3, "quatre": 4,
    "cinq": 5, "six": 6, "sept": 7, "huit": 8, "neuf": 9, "dix": 10,
}

def _word_to_int(word: str) -> int:
    try:
        return int(word)
    except ValueError:
        return _FR_NUMBERS.get(word.lower(), 1)


# ── utilitaire ────────────────────────────────────────────────────────────────

def _reply(
    message: dict[str, Any],
    client: zulip.Client,
    response: dict[str, Any],
) -> None:
    msg_type = message.get("type")
    payload: dict[str, Any] = {
        "type": msg_type,
        "content": response.get("content", ""),
    }

    if msg_type == "stream" and response.get("widget_content"):
        payload["widget_content"] = response["widget_content"]

    if msg_type == "stream":
        payload["to"] = message["display_recipient"]
        payload["topic"] = message["subject"]
    else:
        payload["to"] = [message["sender_email"]]

    if "widget_content" in payload:
        log.debug("Envoi zform widget_content=%s", payload["widget_content"][:120])
    result = client.send_message(payload)
    log.debug("send_message result: %s", result)
    if result.get("result") != "success":
        log.error("send_message erreur: %s", result)
