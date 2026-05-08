import json
from typing import Any

from src.nextcloud.client import NextcloudFile

# 26 lettres suffisent pour max_results=20
_LABELS = [chr(65 + i) for i in range(26)]


def recent_files_form(files: list[NextcloudFile], days: int) -> dict[str, Any]:
    if not files:
        return {
            "content": f"Aucun fichier modifié ces {days} derniers jours.",
            "widget_content": None,
        }

    file_choices = [
        {
            "type": "multiple_choice",
            "short_name": _LABELS[i],
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
                "heading": f"Fichiers Nextcloud — {days} derniers jours",
                "choices": file_choices + [validate_choice],
            },
        }
    )

    return {
        "content": f"**{len(files)} fichier(s) récent(s)** — sélectionnez puis cliquez Valider :",
        "widget_content": widget_content,
    }


def file_link(file: NextcloudFile) -> str:
    return f"[{file.name}]({file.open_link})"


def origin_message(user_name: str, files: list[NextcloudFile]) -> str:
    n = len(files)
    header = (
        f"**{user_name}** a lié le fichier suivant :"
        if n == 1 else
        f"**{user_name}** a lié les fichiers suivants :"
    )
    links = "\n".join(f"- {file_link(f)}" for f in files)
    return f"{header}\n{links}"


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
