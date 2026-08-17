from __future__ import annotations

import re
from collections import deque
from dataclasses import dataclass
from urllib.parse import quote, urlparse

import httpx

from ukb.config import Settings
from ukb.ingestion_models import DriveIngestionRequest
from ukb.services.ingestion import RawIngestionItem


class GoogleDriveConnectorError(RuntimeError):
    pass


@dataclass(frozen=True)
class DriveCollection:
    items: list[RawIngestionItem]
    warnings: list[str]


class GoogleDriveConnector:
    """Server-side Google Drive folder collector using an operator OAuth token."""

    DRIVE_API = "https://www.googleapis.com/drive/v3"
    EXPORTS = {
        "application/vnd.google-apps.document": (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ".docx",
        ),
        "application/vnd.google-apps.spreadsheet": (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            ".xlsx",
        ),
        "application/vnd.google-apps.presentation": (
            "application/vnd.openxmlformats-officedocument.presentationml.presentation",
            ".pptx",
        ),
        "application/vnd.google-apps.drawing": ("application/pdf", ".pdf"),
    }

    def __init__(self, settings: Settings):
        self.settings = settings

    def collect(self, request: DriveIngestionRequest) -> DriveCollection:
        if not self.settings.google_drive_enabled:
            raise GoogleDriveConnectorError("Google Drive ingestion is disabled.")
        if not self.settings.google_drive_access_token:
            raise GoogleDriveConnectorError(
                "Google Drive requires the server-side UKB_GOOGLE_DRIVE_ACCESS_TOKEN."
            )
        folder_id = self.folder_id(request.folder_url)
        headers = {"Authorization": f"Bearer {self.settings.google_drive_access_token}"}
        items: list[RawIngestionItem] = []
        warnings: list[str] = []
        queue: deque[tuple[str, str]] = deque([(folder_id, request.title)])
        visited: set[str] = set()

        with httpx.Client(
            headers=headers,
            timeout=self.settings.google_drive_timeout_seconds,
            follow_redirects=False,
        ) as client:
            while queue and len(items) < request.max_files:
                current_id, parent_path = queue.popleft()
                if current_id in visited:
                    continue
                visited.add(current_id)
                for metadata in self._list_children(client, current_id):
                    if len(items) >= request.max_files:
                        break
                    file_id = str(metadata.get("id", ""))
                    name = self._safe_name(str(metadata.get("name", "unnamed")))
                    mime_type = str(metadata.get("mimeType", "application/octet-stream"))
                    if mime_type == "application/vnd.google-apps.folder":
                        if request.recursive:
                            queue.append((file_id, f"{parent_path}/{name}"))
                        continue
                    if mime_type == "application/vnd.google-apps.shortcut":
                        warnings.append(f"Skipped Drive shortcut: {parent_path}/{name}")
                        continue
                    try:
                        data, output_type, suffix = self._download(client, file_id, mime_type)
                    except GoogleDriveConnectorError as exc:
                        warnings.append(f"Skipped {parent_path}/{name}: {exc}")
                        continue
                    if suffix and not name.casefold().endswith(suffix):
                        name += suffix
                    items.append(
                        RawIngestionItem(
                            name=name,
                            path=f"{parent_path}/{name}",
                            data=data,
                            content_type=output_type,
                            source_uri=str(metadata.get("webViewLink") or f"https://drive.google.com/open?id={file_id}"),
                        )
                    )
        if queue:
            warnings.append(f"Stopped after the configured {request.max_files}-file limit.")
        if not items:
            warnings.append("No downloadable or exportable files were found in the folder.")
        return DriveCollection(items=items, warnings=warnings)

    @staticmethod
    def folder_id(folder_url: str) -> str:
        value = folder_url.strip()
        patterns = [
            r"/folders/([A-Za-z0-9_-]+)",
            r"[?&]id=([A-Za-z0-9_-]+)",
        ]
        for pattern in patterns:
            match = re.search(pattern, value)
            if match:
                return match.group(1)
        if re.fullmatch(r"[A-Za-z0-9_-]{10,}", value):
            return value
        raise GoogleDriveConnectorError("The Google Drive folder URL does not contain a folder ID.")

    def _list_children(self, client: httpx.Client, folder_id: str) -> list[dict]:
        files: list[dict] = []
        page_token: str | None = None
        while True:
            params = {
                "q": f"'{folder_id}' in parents and trashed = false",
                "fields": "nextPageToken,files(id,name,mimeType,size,modifiedTime,webViewLink)",
                "pageSize": 100,
                "supportsAllDrives": "true",
                "includeItemsFromAllDrives": "true",
            }
            if page_token:
                params["pageToken"] = page_token
            response = client.get(f"{self.DRIVE_API}/files", params=params)
            if response.status_code >= 400:
                raise GoogleDriveConnectorError(
                    f"Drive list request failed ({response.status_code}): {response.text[:300]}"
                )
            payload = response.json()
            raw_files = payload.get("files", [])
            if isinstance(raw_files, list):
                files.extend(item for item in raw_files if isinstance(item, dict))
            page_token = payload.get("nextPageToken")
            if not page_token:
                return files

    def _download(
        self,
        client: httpx.Client,
        file_id: str,
        mime_type: str,
    ) -> tuple[bytes, str, str]:
        if mime_type.startswith("application/vnd.google-apps."):
            export = self.EXPORTS.get(mime_type)
            if export is None:
                raise GoogleDriveConnectorError(f"Google-native type is not supported: {mime_type}")
            output_type, suffix = export
            url = f"{self.DRIVE_API}/files/{quote(file_id, safe='')}/export"
            response = client.get(url, params={"mimeType": output_type})
        else:
            output_type, suffix = mime_type, ""
            url = f"{self.DRIVE_API}/files/{quote(file_id, safe='')}"
            response = client.get(url, params={"alt": "media", "supportsAllDrives": "true"})
        if response.status_code >= 400:
            raise GoogleDriveConnectorError(
                f"download failed ({response.status_code}): {response.text[:200]}"
            )
        if len(response.content) > self.settings.max_upload_bytes:
            raise GoogleDriveConnectorError("file exceeds the configured UKB upload limit")
        return response.content, output_type, suffix

    @staticmethod
    def _safe_name(name: str) -> str:
        parsed = urlparse(name)
        candidate = parsed.path if parsed.scheme else name
        safe = re.sub(r"[\\/:*?\"<>|]+", "-", candidate).strip(" .-")
        return safe or "drive-file"
