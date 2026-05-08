import json
from typing import Any

from src.nextcloud.client import NextcloudFile


def recent_files_form(files: list[NextcloudFile], days: int) -> dict[str, Any]:
    if not files:
        return {
            "content": f"Aucun fichier modifié ces {days} derniers jours.",
            "widget_content": None,
        }

    file_choices = [
        {
            "type": "multiple_choice",
            "short_name": str(i),
            "long_name": _format_label(f),
            "reply": f"link_file:{f.path}",
        }
        for i, f in enumerate(files)
    ]
    validate_choice = {
        "type": "multiple_choice",
        "short_name": "✓",
        "long_name": "── Valider la sélection ──",
        "reply": "validate_selection",
    }

    widget_content = json.dumps(
        {
            "widget_type": "zform",
            "extra_data": {
                "type": "choices",
                "heading": f"Fichiers Nextcloud — {days} derniers jours\nCliquez pour sélectionner, puis Valider",
                "choices": file_choices + [validate_choice],
            },
        }
    )

    return {
        "content": f"**{len(files)} fichier(s) récent(s)** — sélectionnez puis cliquez Valider :",
        "widget_content": widget_content,
    }


def recent_files_text(files: list[NextcloudFile], days: int) -> str:
    """Fallback texte pour les DMs (les widgets ne s'y affichent pas)."""
    if not files:
        return f"Aucun fichier modifié ces {days} derniers jours."
    lines = [f"**{len(files)} fichier(s) récent(s)** (ces {days} derniers jours) :\n"]
    for f in files:
        date_str = f.modified.strftime("%d/%m %H:%M") if f.modified else "?"
        lines.append(f"- [{f.name}]({f.open_link}) — {date_str}, {_human_size(f.size)}")
    return "\n".join(lines)


def file_link_message(file: NextcloudFile) -> str:
    """Texte Markdown posté dans la conversation quand un fichier est sélectionné."""
    date_str = file.modified.strftime("%d/%m/%Y %H:%M") if file.modified else "?"
    return (
        f"**Fichier lié :** [{file.name}]({file.open_link})  \n"
        f"Modifié le {date_str} · {_human_size(file.size)}"
    )


# ── helpers ───────────────────────────────────────────────────────────────────

def _format_label(f: NextcloudFile) -> str:
    date_str = f.modified.strftime("%d/%m %H:%M") if f.modified else "?"
    return f"{f.name}  ({date_str}, {_human_size(f.size)})"


def _human_size(size: int) -> str:
    for unit in ("o", "Ko", "Mo", "Go"):
        if size < 1024:
            return f"{size:.0f} {unit}"
        size /= 1024
    return f"{size:.1f} To"
