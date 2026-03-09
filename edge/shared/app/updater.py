import json
from dataclasses import dataclass
from typing import Dict, List, Optional

from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import CONFIG_PATH, CONFIG_STAGING_PATH, Config
from edge.shared.app.endpoints import OTA_CHECK_PATH, OTA_FILE_PATH
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
        logger=None,
    ):
        self._fs = fs
        self._http = http
        self._system = system
        self._config = config
        self._boot_manager = boot_manager
        self._staging_root = staging_root
        self._logger = logger

    def check(self) -> Optional[UpdateInfo]:
        url = self._config.api_url + OTA_CHECK_PATH
        headers = self._auth_headers()
        headers["X-Current-Version"] = self._config.current_version

        self._log_info("Sending OTA check request", {"url": url, "current_version": self._config.current_version})
        response = self._http.get(url, headers=headers)
        if response.status_code != 200:
            self._log_warn("OTA check failed", {"status_code": response.status_code})
            return None

        payload = json.loads(response.text)
        if not payload.get("available"):
            self._log_info("No OTA update available")
            return None

        self._log_info("OTA update available", {"version": payload.get("version")})

        return UpdateInfo(
            available=True,
            version=payload["version"],
            manifest=payload.get("manifest", []),
        )

    def apply(self, update_info: UpdateInfo) -> None:
        self._log_info("Applying OTA update", {"version": update_info.version})
        self._clear_staging()
        self._ensure_dir(self._staging_root)

        config_staged = False
        for item in update_info.manifest:
            rel_path = item["path"]
            expected_hash = item["hash"]
            self._log_info("Downloading OTA file", {"path": rel_path})
            content = self._download_file(update_info.version, rel_path)
            target_path = self._config_staging_target() if rel_path == CONFIG_PATH else self._join(self._staging_root, rel_path)
            self._ensure_dir(self._parent_dir(target_path))
            atomic_write_bytes(self._fs, target_path, content)
            self._log_info("OTA file written to staging", {"path": rel_path, "bytes": len(content)})

            if rel_path == CONFIG_PATH:
                config_staged = True

            actual_hash = self._digest_bytes(content)
            if actual_hash.lower() != expected_hash.lower():
                self._clear_staging()
                self._log_error("OTA file hash mismatch", {"path": rel_path})
                raise ValueError("Hash mismatch for " + rel_path)

        if config_staged:
            self._log_info("Validating staged config", {"path": CONFIG_STAGING_PATH})
            try:
                Config.load(self._fs, path=CONFIG_STAGING_PATH, system=self._system)
            except Exception:
                self._clear_staging()
                self._log_error("Staged config validation failed")
                raise

        self._boot_manager.set_new_version(update_info.version)
        self._log_info("OTA apply complete, resetting", {"version": update_info.version})
        self._system.reset()

    def _download_file(self, version: str, path: str) -> bytes:
        url = self._config.api_url + OTA_FILE_PATH + "?version=" + version + "&path=" + path
        response = self._http.get(url, headers=self._auth_headers())
        if response.status_code != 200:
            self._log_error("OTA file download failed", {"path": path, "status_code": response.status_code})
            raise RuntimeError("Failed to download update file: " + path)
        return response.content

    def _auth_headers(self) -> Dict[str, str]:
        return {
            "X-Device-ID": self._config.device_id,
            "X-Api-Key": self._config.api_key,
        }

    def _clear_staging(self) -> None:
        self._remove_tree(self._staging_root)
        self._remove_tree(CONFIG_STAGING_PATH)

    @staticmethod
    def _config_staging_target() -> str:
        return CONFIG_STAGING_PATH

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

    def _log_info(self, message: str, context=None) -> None:
        if self._logger is not None:
            self._logger.info(message, context)

    def _log_warn(self, message: str, context=None) -> None:
        if self._logger is not None:
            self._logger.warn(message, context)

    def _log_error(self, message: str, context=None) -> None:
        if self._logger is not None:
            self._logger.error(message, context)
