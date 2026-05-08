import re
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from typing import Optional
from urllib.parse import quote, unquote
from xml.etree import ElementTree as ET

import requests
from requests.auth import HTTPBasicAuth

from src import config

_DAV = "DAV:"
_OC = "http://owncloud.org/ns"

_PROPFIND_BODY = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<d:propfind xmlns:d="DAV:" xmlns:oc="http://owncloud.org/ns">'
    "<d:prop>"
    "<d:displayname/>"
    "<d:getlastmodified/>"
    "<d:getcontentlength/>"
    "<d:getcontenttype/>"
    "<d:resourcetype/>"
    "<oc:fileid/>"
    "</d:prop>"
    "</d:propfind>"
)

_WEBDAV_PATH_RE = re.compile(r"^/remote\.php/(?:dav|webdav)/files/[^/]+(/.*)?$")


@dataclass
class NextcloudFile:
    name: str
    path: str           # chemin logique depuis la racine, ex : /Documents/test.md
    file_id: Optional[int]
    modified: Optional[datetime]
    size: int
    content_type: str
    is_dir: bool

    @property
    def open_link(self) -> str:
        if self.file_id:
            return (
                f"{config.NEXTCLOUD_URL}/apps/files/files/{self.file_id}"
                "?dir=/&openfile=true"
            )
        # fallback sans file_id
        directory = self.path.rsplit("/", 1)[0] or "/"
        return f"{config.NEXTCLOUD_URL}/apps/files/?dir={quote(directory)}"


class NextcloudClient:
    def __init__(self) -> None:
        self._base = (
            f"{config.NEXTCLOUD_URL}/remote.php/dav/files/{config.NEXTCLOUD_USER}"
        )
        self._session = requests.Session()
        self._session.auth = HTTPBasicAuth(config.NEXTCLOUD_USER, config.NEXTCLOUD_PASSWORD)

    def recent_files(
        self,
        days: int = config.RECENT_DAYS,
        max_results: int = 20,
        path: str = "/",
    ) -> list[NextcloudFile]:
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        files = [
            f for f in self._propfind(path, depth="infinity")
            if not f.is_dir and f.modified and f.modified >= cutoff
        ]
        files.sort(key=lambda f: f.modified, reverse=True)
        return files[:max_results]

    def file_info(self, path: str) -> Optional[NextcloudFile]:
        results = self._propfind(path, depth="0")
        return results[0] if results else None

    def _propfind(self, path: str, depth: str = "1") -> list[NextcloudFile]:
        url = self._base.rstrip("/") + "/" + path.lstrip("/")
        resp = self._session.request(
            "PROPFIND",
            url,
            data=_PROPFIND_BODY.encode(),
            headers={"Content-Type": "application/xml", "Depth": depth},
        )
        resp.raise_for_status()
        return _parse_multistatus(resp.text)


def _parse_multistatus(xml_text: str) -> list[NextcloudFile]:
    root = ET.fromstring(xml_text)
    files: list[NextcloudFile] = []

    for response in root.findall(f"{{{_DAV}}}response"):
        href = response.findtext(f"{{{_DAV}}}href", "")
        props = response.find(f".//{{{_DAV}}}prop")
        if props is None:
            continue

        resource_type = props.find(f"{{{_DAV}}}resourcetype")
        is_dir = (
            resource_type is not None
            and resource_type.find(f"{{{_DAV}}}collection") is not None
        )

        logical_path = _logical_path(href)
        display_name = props.findtext(f"{{{_DAV}}}displayname")
        name = display_name or logical_path.rstrip("/").rsplit("/", 1)[-1] or href

        modified = _parse_http_date(props.findtext(f"{{{_DAV}}}getlastmodified"))

        try:
            size = int(props.findtext(f"{{{_DAV}}}getcontentlength") or "0")
        except ValueError:
            size = 0

        content_type = props.findtext(f"{{{_DAV}}}getcontenttype") or ""

        file_id_str = props.findtext(f"{{{_OC}}}fileid")
        try:
            file_id: Optional[int] = int(file_id_str) if file_id_str else None
        except ValueError:
            file_id = None

        files.append(
            NextcloudFile(
                name=name,
                path=logical_path,
                file_id=file_id,
                modified=modified,
                size=size,
                content_type=content_type,
                is_dir=is_dir,
            )
        )

    return files


def _logical_path(href: str) -> str:
    decoded = unquote(href)
    m = _WEBDAV_PATH_RE.match(decoded)
    if m:
        return m.group(1) or "/"
    return decoded


def _parse_http_date(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    try:
        return parsedate_to_datetime(value).astimezone(timezone.utc)
    except Exception:
        pass
    for fmt in ("%Y-%m-%dT%H:%M:%SZ", "%a, %d %b %Y %H:%M:%S %Z"):
        try:
            return datetime.strptime(value, fmt).replace(tzinfo=timezone.utc)
        except ValueError:
            continue
    return None
