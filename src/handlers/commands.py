import logging
from datetime import datetime, timezone
from typing import Any

import zulip

from src import config
from src.nextcloud.client import NextcloudClient
from src.handlers import dm_flow

log = logging.getLogger(__name__)
_nc = NextcloudClient()

USAGE = """\
**Bot Nextcloud — commandes disponibles**

- `recent` — fichiers modifiés ces 7 derniers jours
- `recent <N>` — fichiers des N derniers jours
- `recent <durée>` — ex : `recent une semaine`, `recent 2 mois`
- `help` — affiche cette aide
"""


def handle(message: dict[str, Any], client: zulip.Client) -> None:
    content: str = message.get("content", "").strip()
    args = content.split()

    if not args or args[0].lower() == "help":
        _reply(message, client, USAGE)
        return

    cmd = args[0].lower()
    if cmd == "recent":
        _cmd_recent(message, client, args[1:])
    else:
        _reply(message, client, f"Commande inconnue : `{cmd}`. Tapez `help`.")


def _cmd_recent(
    message: dict[str, Any],
    client: zulip.Client,
    args: list[str],
) -> None:
    days = config.RECENT_DAYS
    if args:
        days = _parse_days(" ".join(args))
        if days is None:
            _reply(message, client,
                   "Argument non reconnu. Essayez `recent 7`, `recent une semaine`, `recent 2 mois`.")
            return

    try:
        files = _nc.recent_files(days=days)
    except Exception as exc:
        log.exception("Erreur Nextcloud")
        _reply(message, client, f"Erreur Nextcloud : {exc}")
        return

    dm_flow.start(message, client, files, days)


def _reply(message: dict[str, Any], client: zulip.Client, content: str) -> None:
    msg_type = message.get("type")
    payload: dict[str, Any] = {"type": msg_type, "content": content}
    if msg_type == "stream":
        payload["to"] = message["display_recipient"]
        payload["topic"] = message["subject"]
    else:
        payload["to"] = [message["sender_email"]]
    client.send_message(payload)


# ── parsing de durée ──────────────────────────────────────────────────────────

def _parse_days(text: str) -> int | None:
    text = text.strip().lower()
    try:
        return max(1, int(text))
    except ValueError:
        pass
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
            return max(1, (now - parsed).days)
    except ImportError:
        pass
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
