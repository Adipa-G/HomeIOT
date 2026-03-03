import json
from dataclasses import dataclass
from typing import Dict, List, Optional

from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import Config
from edge.shared.app.safe_io import atomic_write_bytes
from edge.shared.hal.interfaces import IFileSystem, IHttpClient, ISystem


@dataclass
class UpdateInfo:
    available: bool
    version: str
    manifest: List[Dict]


class Updater:
    def __init__(
        self,
        fs: IFileSystem,
        http: IHttpClient,
        system: ISystem,
        config: Config,
        boot_manager: BootManager,
        staging_root: str = "app_staging",
    ):
        self._fs = fs
        self._http = http
        self._system = system
        self._config = config
        self._boot_manager = boot_manager
        self._staging_root = staging_root

    def check(self) -> Optional[UpdateInfo]:
        url = self._config.api_url + "/api/ota/check"
        headers = self._auth_headers()
        headers["X-Current-Version"] = self._config.current_version

        response = self._http.get(url, headers=headers)
        if response.status_code != 200:
            return None

        payload = json.loads(response.text)
        if not payload.get("available"):
            return None

        return UpdateInfo(
            available=True,
            version=payload["version"],
            manifest=payload.get("manifest", []),
        )

    def apply(self, update_info: UpdateInfo) -> None:
        self._clear_staging()
        self._ensure_dir(self._staging_root)

        for item in update_info.manifest:
            rel_path = item["path"]
            expected_hash = item["hash"]
            content = self._download_file(update_info.version, rel_path)
            target_path = self._join(self._staging_root, rel_path)
            self._ensure_dir(self._parent_dir(target_path))
            atomic_write_bytes(self._fs, target_path, content)

            actual_hash = self._digest_bytes(content)
            if actual_hash.lower() != expected_hash.lower():
                self._clear_staging()
                raise ValueError("Hash mismatch for " + rel_path)

        self._boot_manager.set_new_version(update_info.version)
        self._system.reset()

    def _download_file(self, version: str, path: str) -> bytes:
        url = self._config.api_url + "/api/ota/file?version=" + version + "&path=" + path
        response = self._http.get(url, headers=self._auth_headers())
        if response.status_code != 200:
            raise RuntimeError("Failed to download update file: " + path)
        return response.content

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "X-Device-ID": self._config.device_id,
            "X-Api-Key": self._config.api_key,
        }

    def _clear_staging(self) -> None:
        self._remove_tree(self._staging_root)

    def _remove_tree(self, path: str) -> None:
        if not self._fs.exists(path):
            return

        if self._fs.is_dir(path):
            for name in self._fs.listdir(path):
                self._remove_tree(self._join(path, name))
            self._fs.rmdir(path)
            return

        self._fs.remove(path)

    def _ensure_dir(self, path: str) -> None:
        if path and not self._fs.exists(path):
            self._fs.makedirs(path)

    @staticmethod
    def _join(left: str, right: str) -> str:
        if not left:
            return right
        if left.endswith("/"):
            return left + right
        return left + "/" + right

    @staticmethod
    def _parent_dir(path: str) -> str:
        if "/" not in path:
            return ""
        return path.rsplit("/", 1)[0]

    @staticmethod
    def _digest_bytes(data: bytes) -> str:
        try:
            import uhashlib as hashlib
        except ImportError:  # pragma: no cover - desktop fallback
            import hashlib

        digest = hashlib.sha256(data).digest()
        return "".join("{:02x}".format(byte) for byte in digest)
