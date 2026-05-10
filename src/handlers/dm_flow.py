import logging
from dataclasses import dataclass, field
from typing import Any

import zulip

from src import config
from src.nextcloud.client import NextcloudClient, NextcloudFile
from src.zulip_ui import forms

log = logging.getLogger(__name__)
_nc = NextcloudClient()

_LINK_PREFIX = "link_file:"
_VALIDATE_CMD = "validate_selection"

_sessions: dict[str, "DMSession"] = {}


@dataclass
class DMSession:
    origin_type: str
    origin_stream_id: int | None
    origin_to: Any
    origin_topic: str
    origin_message_id: int
    origin_user_name: str
    files: list[NextcloudFile]
    days: int
    selected: list[int] = field(default_factory=list)


def has_session(user_email: str) -> bool:
    return user_email in _sessions


def start(
    trigger: dict[str, Any],
    client: zulip.Client,
    files: list[NextcloudFile],
    days: int,
) -> None:
    user_email = trigger["sender_email"]

    if user_email in _sessions:
        del _sessions[user_email]

    if not files:
        _dm_send(user_email, client,
                 f"Aucun fichier modifié ces {days} derniers jours.")
        return

    msg_type = trigger.get("type")
    _sessions[user_email] = DMSession(
        origin_type=msg_type,
        origin_stream_id=trigger.get("stream_id"),
        origin_to=(
            trigger["display_recipient"] if msg_type == "stream"
            else [user_email]
        ),
        origin_topic=trigger.get("subject", ""),
        origin_message_id=trigger["id"],
        origin_user_name=trigger.get("sender_full_name", user_email),
        files=files,
        days=days,
    )

    if msg_type == "stream" and config.ALLOW_MESSAGE_DELETE:
        del_result = client.call_endpoint(
            url=f"messages/{trigger['id']}",
            method="DELETE",
        )
        if del_result.get("result") != "success":
            log.warning("Suppression message %d impossible : %s", trigger["id"], del_result)

    response = forms.recent_files_form(files, days)
    result = client.send_message({
        "type": "private",
        "to": [user_email],
        "content": response["content"],
        "widget_content": response["widget_content"],
    })
    log.debug("DM zform envoyé : %s", result)


def handle(message: dict[str, Any], client: zulip.Client) -> None:
    user_email = message["sender_email"]
    session = _sessions.get(user_email)
    if session is None:
        return

    content = message["content"].strip()

    if content.startswith(_LINK_PREFIX):
        path = content[len(_LINK_PREFIX):]
        idx = next((i for i, f in enumerate(session.files) if f.path == path), None)
        if idx is None:
            log.warning("Chemin non reconnu dans link_file de %s : %s", user_email, path)
        elif idx not in session.selected:
            session.selected.append(idx)
            log.debug("Sélection : %s", path)
        return

    if content == _VALIDATE_CMD:
        if not session.selected:
            _dm_send(user_email, client, "Aucun fichier sélectionné.")
            return
        _validate(user_email, session, client)
        return

    if content.lower() == "annuler":
        del _sessions[user_email]
        _dm_send(user_email, client, "Sélection annulée.")


def _validate(user_email: str, session: DMSession, client: zulip.Client) -> None:
    try:
        selected_files = [session.files[i] for i in session.selected]
        payload: dict[str, Any] = {
            "type": session.origin_type,
            "content": forms.origin_message(session.origin_user_name, selected_files),
        }
        if session.origin_type == "stream":
            payload["to"] = session.origin_to
            payload["topic"] = session.origin_topic
        else:
            payload["to"] = session.origin_to

        result = client.send_message(payload)
        log.debug("Post vers origine : %s", result)

        msg_link = _message_link(session, result.get("id"))
        _dm_send(user_email, client, f"✓ Fichiers liés dans la [conversation]({msg_link}).")
    except Exception:
        log.exception("Erreur lors de la validation pour %s", user_email)
        try:
            _dm_send(user_email, client, "Une erreur est survenue, veuillez réessayer.")
        except Exception:
            log.exception("Impossible d'envoyer le message d'erreur à %s", user_email)
    finally:
        _sessions.pop(user_email, None)


def _message_link(session: DMSession, message_id: int | None) -> str:
    if session.origin_type != "stream" or not message_id:
        return config.ZULIP_SITE
    stream_id = session.origin_stream_id
    channel = _encode_channel(session.origin_to)
    topic = _encode_component(session.origin_topic)
    channel_part = f"{stream_id}-{channel}" if stream_id else channel
    return f"{config.ZULIP_SITE}/#narrow/channel/{channel_part}/topic/{topic}/with/{message_id}"


def _encode_channel(name: str) -> str:
    """Espaces → tirets, puis encodage Zulip."""
    return _encode_component(name.replace(" ", "-"))


def _encode_component(text: str) -> str:
    """Équivalent de encodeHashComponent() de Zulip :
    encodeURIComponent → échappe les points → remplace % par ."""
    from urllib.parse import quote  # noqa: PLC0415
    encoded = quote(text, safe="")          # encode tout sauf les caractères non-réservés
    encoded = encoded.replace(".", "%2E")   # échappe les points littéraux
    encoded = encoded.replace("%", ".")     # %XX → .XX
    return encoded


def _dm_send(user_email: str, client: zulip.Client, content: str) -> None:
    client.send_message({"type": "private", "to": [user_email], "content": content})


def _human_size(size: int) -> str:
    for unit in ("o", "Ko", "Mo", "Go"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} To"
