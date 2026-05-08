from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Optional

import webdav3.client as wc

from src import config


@dataclass
class NextcloudFile:
    name: str
    path: str          # chemin relatif depuis la racine de l'utilisateur
    modified: datetime
    size: int
    content_type: str
    is_dir: bool

    @property
    def internal_link(self) -> str:
        """Lien interne Nextcloud (ouverture dans Files)."""
        encoded = self.path.replace(" ", "%20")
        return f"{config.NEXTCLOUD_URL}/apps/files/?dir={encoded}"

    @property
    def webdav_url(self) -> str:
        encoded = self.path.replace(" ", "%20")
        return (
            f"{config.NEXTCLOUD_URL}/remote.php/dav/files/"
            f"{config.NEXTCLOUD_USER}{encoded}"
        )


class NextcloudClient:
    def __init__(self) -> None:
        options = {
            "webdav_hostname": (
                f"{config.NEXTCLOUD_URL}/remote.php/dav/files/{config.NEXTCLOUD_USER}"
            ),
            "webdav_login": config.NEXTCLOUD_USER,
            "webdav_password": config.NEXTCLOUD_PASSWORD,
        }
        self._client = wc.Client(options)

    def recent_files(
        self,
        days: int = config.RECENT_DAYS,
        max_results: int = 20,
        path: str = "/",
    ) -> list[NextcloudFile]:
        """Retourne les fichiers modifiés dans les `days` derniers jours."""
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        raw = self._client.list(path, get_info=True)
        files: list[NextcloudFile] = []

        for item in raw:
            if item.get("isdir"):
                continue
            modified = self._parse_date(item.get("modified", ""))
            if modified and modified >= cutoff:
                files.append(
                    NextcloudFile(
                        name=item["name"],
                        path=item["path"],
                        modified=modified,
                        size=int(item.get("size", 0)),
                        content_type=item.get("content_type", ""),
                        is_dir=False,
                    )
                )

        files.sort(key=lambda f: f.modified, reverse=True)
        return files[:max_results]

    def file_info(self, path: str) -> Optional[NextcloudFile]:
        """Retourne les métadonnées d'un fichier."""
        try:
            info = self._client.info(path)
            return NextcloudFile(
                name=info["name"],
                path=path,
                modified=self._parse_date(info.get("modified", "")),
                size=int(info.get("size", 0)),
                content_type=info.get("content_type", ""),
                is_dir=info.get("isdir", False),
            )
        except Exception:
            return None

    @staticmethod
    def _parse_date(value: str) -> Optional[datetime]:
        if not value:
            return None
        for fmt in ("%a, %d %b %Y %H:%M:%S %Z", "%Y-%m-%dT%H:%M:%SZ"):
            try:
                dt = datetime.strptime(value, fmt)
                return dt.replace(tzinfo=timezone.utc)
            except ValueError:
                continue
        return None
