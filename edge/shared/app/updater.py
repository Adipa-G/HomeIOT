import json

from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import CONFIG_PATH, CONFIG_STAGING_PATH, Config
from edge.shared.app.endpoints import OTA_CHECK_PATH, OTA_FILE_PATH
from edge.shared.app.safe_io import atomic_write_bytes
from edge.shared.app.secret_crypto import encrypt_secret
from edge.shared.hal.interfaces import IFileSystem, IHttpClient, ISystem


class UpdateInfo:
    def __init__(self, available, version, manifest):
        self.available = bool(available)
        self.version = str(version)
        self.manifest = list(manifest)


class Updater:
    def __init__(
        self,
        fs: IFileSystem,
        http: IHttpClient,
        system: ISystem,
        config: Config,
        boot_manager: BootManager,
        staging_root: str = "app_staging",
        platform: str = "esp32",
        logger=None,
    ):
        self._fs = fs
        self._http = http
        self._system = system
        self._config = config
        self._boot_manager = boot_manager
        self._staging_root = staging_root
        self._platform = platform
        self._logger = logger

    def check(self):
        url = self._config.api_url + OTA_CHECK_PATH + "?version=" + self._config.current_version
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
        try:
            import gc as _gc
        except ImportError:  # pragma: no cover - desktop fallback
            _gc = None

        # Pause log uplink during OTA to avoid socket contention;
        # log entries still buffer and print to console.
        uplink_paused = False
        if self._logger is not None and hasattr(self._logger, "pause_uplink"):
            self._logger.pause_uplink()
            uplink_paused = True

        try:
            self._log_info("Applying OTA update", {"version": update_info.version})
            self._clear_staging()
            self._ensure_dir(self._staging_root)

            config_staged = False
            for item in update_info.manifest:
                rel_path = item["path"]
                expected_hash = item["hash"]
                downloaded_content = self._download_file(update_info.version, rel_path)

                actual_hash = self._digest_bytes(downloaded_content)
                if actual_hash.lower() != expected_hash.lower():
                    self._clear_staging()
                    self._log_error("OTA file hash mismatch", {"path": rel_path})
                    raise ValueError("Hash mismatch for " + rel_path)

                content = downloaded_content

                if rel_path == CONFIG_PATH:
                    content = self._merge_config_payload(content, update_info.version)

                target_path = self._config_staging_target() if rel_path == CONFIG_PATH else self._join(self._staging_root, rel_path)
                self._ensure_dir(self._parent_dir(target_path))
                atomic_write_bytes(self._fs, target_path, content)
                self._log_info("OTA file written to staging", {"path": rel_path, "bytes": len(content)})

                if rel_path == CONFIG_PATH:
                    config_staged = True

                # Release buffers immediately and run GC to avoid heap exhaustion
                # on memory-constrained devices when downloading many files.
                downloaded_content = None
                content = None
                actual_hash = None
                if _gc is not None:
                    _gc.collect()

                # Brief pause between downloads to yield to the RTOS scheduler
                # and let flash I/O settle.  TCP TIME_WAIT is handled at the
                # HTTP-client layer via SO_LINGER(0).
                self._system.sleep_ms(50)

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
        finally:
            if uplink_paused:
                self._logger.resume_uplink()

    def _download_file(self, version: str, path: str, retries: int = 3) -> bytes:
        url = self._config.api_url + OTA_FILE_PATH + "?version=" + version + "&path=" + path
        last_error = None
        for attempt in range(retries):
            if attempt > 0:
                delay_ms = 500 * attempt
                self._log_warn("Retrying OTA download", {"path": path, "attempt": attempt + 1, "delay_ms": delay_ms})
                self._system.sleep_ms(delay_ms)
            try:
                response = self._http.get(url, headers=self._auth_headers())
                if response.status_code == 200:
                    return response.content
                last_error = "HTTP " + str(response.status_code)
                self._log_warn("OTA download got non-200", {"path": path, "status_code": response.status_code})
            except Exception as exc:
                last_error = str(exc)
                self._log_warn("OTA download error", {"path": path, "error": last_error})
        self._log_error("OTA file download failed after retries", {"path": path, "error": last_error})
        raise RuntimeError("Failed to download update file: " + path)

    def _auth_headers(self):
        return {
            "X-Device-ID": self._config.device_id,
            "X-Api-Key": self._config.api_key,
            "X-Platform": self._platform,
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
        try:
            from ubinascii import hexlify
            return str(hexlify(digest), "ascii")
        except ImportError:  # pragma: no cover - desktop fallback
            return digest.hex()

    def _log_info(self, message: str, context=None) -> None:
        if self._logger is not None:
            self._logger.info(message, context)

    def _log_warn(self, message: str, context=None) -> None:
        if self._logger is not None:
            self._logger.warn(message, context)

    def _log_error(self, message: str, context=None) -> None:
        if self._logger is not None:
            self._logger.error(message, context)

    def _merge_config_payload(self, staged_config: bytes, target_version: str) -> bytes:
        staged = json.loads(staged_config.decode("utf-8"))
        if not self._fs.exists(CONFIG_PATH):
            staged["current_version"] = target_version
            return json.dumps(staged, separators=(",", ":")).encode("utf-8")

        active = json.loads(self._fs.read_text(CONFIG_PATH))

        # Non-secret identity/connection fields: preserve from active when staged is a
        # placeholder or absent.
        non_secret_keys = ["device_id", "api_url", "wifi_ssid"]
        for key in non_secret_keys:
            staged_value = staged.get(key)
            is_placeholder = isinstance(staged_value, str) and staged_value.lower().startswith("replace-with-")
            is_absent = key not in staged
            if is_placeholder or is_absent:
                if key in active:
                    staged[key] = active[key]
                elif is_placeholder:
                    del staged[key]

        # Secret pairs (api_key / wifi_password):
        # - Placeholder or absent  → copy credential from active as-is (enc object preferred)
        # - Real plaintext value   → encrypt on the device, store as _enc, discard plaintext
        # This ensures plaintext secrets are never written to the device filesystem.
        secret_pairs = [("api_key", "api_key_enc"), ("wifi_password", "wifi_password_enc")]
        binding = staged.get("device_id") or self._config.device_id
        for plain_key, enc_key in secret_pairs:
            staged_plain = staged.get(plain_key)
            is_placeholder = isinstance(staged_plain, str) and staged_plain.lower().startswith("replace-with-")
            if is_placeholder or plain_key not in staged:
                # Remove placeholder if present
                staged.pop(plain_key, None)
                # Copy whichever form the active config uses
                if enc_key in active:
                    staged[enc_key] = active[enc_key]
                elif plain_key in active:
                    staged[plain_key] = active[plain_key]
            else:
                # Real plaintext from release → encrypt and store as enc, never plain
                staged[enc_key] = encrypt_secret(staged_plain, binding, plain_key)
                del staged[plain_key]

        staged["current_version"] = target_version
        return json.dumps(staged, separators=(",", ":")).encode("utf-8")
