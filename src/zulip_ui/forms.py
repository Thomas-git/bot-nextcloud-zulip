"""
Constructeurs de messages interactifs Zulip (widget_content type "zform").

Un zform de type "choices" affiche une liste de boutons cliquables.
Quand l'utilisateur clique, Zulip renvoie un message avec le texte `reply`
associé au choix — le bot le traite comme une commande interne.
"""

import json
from typing import Any

from src.nextcloud.client import NextcloudFile


def recent_files_form(files: list[NextcloudFile], days: int) -> dict[str, Any]:
    """
    Construit un message Zulip avec widget_content zform pour la liste
    des fichiers récents.  Retourne un dict prêt à passer à send_message().
    """
    if not files:
        return {
            "content": f"Aucun fichier modifié ces {days} derniers jours.",
            "widget_content": None,
        }

    choices = [
        {
            "short_name": str(i),
            "long_name": _format_label(f),
            # La commande renvoyée au bot quand l'utilisateur clique
            "reply": f"link_file:{f.path}",
        }
        for i, f in enumerate(files)
    ]

    widget_content = json.dumps(
        {
            "widget_type": "zform",
            "extra_data": {
                "type": "choices",
                "heading": f"Fichiers Nextcloud — {days} derniers jours",
                "choices": choices,
            },
        }
    )

    return {
        "content": f"**{len(files)} fichier(s) récent(s)** — cliquez pour lier à la conversation :",
        "widget_content": widget_content,
    }


def file_link_message(file: NextcloudFile) -> str:
    """Texte Markdown posté dans la conversation quand un fichier est sélectionné."""
    size_str = _human_size(file.size)
    date_str = file.modified.strftime("%d/%m/%Y %H:%M") if file.modified else "?"
    return (
        f"**Fichier lié :** [{file.name}]({file.internal_link})  \n"
        f"Modifié le {date_str} · {size_str}"
    )


# ── helpers ──────────────────────────────────────────────────────────────────

def _format_label(f: NextcloudFile) -> str:
    date_str = f.modified.strftime("%d/%m %H:%M") if f.modified else "?"
    size_str = _human_size(f.size)
    return f"{f.name}  ({date_str}, {size_str})"


def _human_size(size: int) -> str:
    for unit in ("o", "Ko", "Mo", "Go"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} To"
