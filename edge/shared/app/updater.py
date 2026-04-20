import json

from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import CONFIG_PATH, CONFIG_STAGING_PATH, Config
from edge.shared.app.endpoints import OTA_CHECK_PATH, OTA_STREAM_PATH
from edge.shared.app.safe_io import atomic_write_bytes
from edge.shared.app.secret_crypto import encrypt_secret
from edge.shared.hal.interfaces import IFileSystem, IHttpClient, ISystem


class _HashingChunkReader:
    """Iterates chunks from a _StreamFrameReader while computing a rolling SHA256.

    Designed to be passed directly to IFileSystem.write_chunks() so the data is
    written to disk one chunk at a time — no large contiguous bytearray needed.
    .digest is populated after the iterator is exhausted.
    """

    def __init__(self, frame_reader, size, hashlib_module):
        self._frame_reader = frame_reader
        self._size = size
        self._h = hashlib_module.sha256()
        self.digest = None

    def __iter__(self):
        for chunk in self._frame_reader.read_chunks(self._size):
            self._h.update(chunk)
            yield chunk
        self.digest = self._h.digest()


_READLINE_BUF_SIZE = 128
_READ_CHUNK_SIZE = 512


class _StreamFrameReader:
    """Reads the OTA framing protocol from a streaming HTTP response.

    Frame format (repeated for each file, then END\\n to terminate):
        HASH:<sha256-hex>\\n
        FILE:<relative/path>\\n
        SIZE:<decimal-byte-count>\\n
        <SIZE raw bytes of file content>
    """

    def __init__(self, streaming_response):
        self._resp = streaming_response
        self._buf = b""
        self._chunk_buf = bytearray(_READ_CHUNK_SIZE)

    def readline(self) -> str:
        while True:
            nl = self._buf.find(b"\n")
            if nl >= 0:
                line = self._buf[:nl].decode("utf-8").rstrip("\r")
                self._buf = self._buf[nl + 1:]
                return line
            chunk = self._resp.read(_READLINE_BUF_SIZE)
            if not chunk:
                raise RuntimeError("Unexpected EOF in OTA stream")
            self._buf = self._buf + chunk

    def read_chunks(self, size: int, chunk_size: int = _READ_CHUNK_SIZE):
        """Yield raw bytes in up-to chunk_size pieces until exactly *size* bytes have been yielded."""
        remaining = size
        # Drain any bytes already pulled into the header look-ahead buffer.
        if self._buf:
            take = min(len(self._buf), remaining)
            yield self._buf[:take]
            self._buf = self._buf[take:]
            remaining -= take
        # Reuse the pre-allocated chunk buffer for all reads — avoids repeated
        # heap allocation that causes GC pressure on a fragmented MicroPython heap.
        mv = memoryview(self._chunk_buf)
        while remaining > 0:
            ask = min(chunk_size, remaining)
            n = self._resp.readinto(mv[:ask])
            if not n:
                raise RuntimeError("Unexpected EOF reading OTA file content")
            remaining -= n
            yield mv[:n]


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

            try:
                config_staged = self._apply_update_streaming(update_info, _gc)
            except Exception:
                # Ensure partial staging is cleaned up on any stream error
                # (hash mismatch already calls _clear_staging internally).
                self._clear_staging()
                raise

            if config_staged:
                self._log_info("Validating staged config", {"path": CONFIG_STAGING_PATH})
                try:
                    Config.load(self._fs, path=CONFIG_STAGING_PATH, system=self._system)
                except Exception:
                    self._clear_staging()
                    self._log_error("Staged config validation failed")
                    raise

            # All files are downloaded and verified — the manifest (30+ dicts
            # with hash strings) is no longer needed.  Releasing it before the
            # version swap frees ~8 KB of scattered heap objects, reducing
            # fragmentation so larger contiguous blocks become available.
            version = update_info.version
            update_info.manifest.clear()
            update_info = None

            # Reclaim heap before the version swap — set_new_version does
            # recursive directory walks and file renames that allocate.
            if _gc is not None:
                _gc.collect()

            self._boot_manager.set_new_version(version)
            self._log_info("OTA apply complete, resetting", {"version": version})

            # Reclaim heap before flush — _decode_buffer + json.dumps of
            # the batch payload is the largest single allocation in the
            # OTA path and can fail on a fragmented heap.
            if _gc is not None:
                _gc.collect()

            # Wait for lwIP to fully release PCBs from the OTA stream socket
            # before opening a new connection for the log flush POST.
            self._system.sleep_ms(2000)

            # Resume uplink and flush before reset so OTA logs reach the
            # server — reset() never returns, so the finally block won't run.
            self._flush_logs()

            self._system.reset()
        finally:
            if uplink_paused:
                self._logger.resume_uplink()

    def _apply_update_streaming(self, update_info: UpdateInfo, _gc) -> bool:
        """Open a single OTA stream and stage all files from it.

        Returns True if config.json was staged (caller must validate it).
        Raises RuntimeError or ValueError on any stream or hash error.
        """
        try:
            import uhashlib as _hashlib
        except ImportError:  # pragma: no cover - desktop fallback
            import hashlib as _hashlib

        try:
            from ubinascii import hexlify as _hexlify

            def _hex(digest):
                return str(_hexlify(digest), "ascii")
        except ImportError:  # pragma: no cover - desktop fallback
            def _hex(digest):
                return digest.hex()

        url = self._config.api_url + OTA_STREAM_PATH + "?version=" + update_info.version
        self._log_info("Opening OTA stream", {"version": update_info.version})
        response = self._http.get_stream(url, headers=self._auth_headers())

        config_staged = False
        file_count = 0
        _ROOT_FILES = ("boot.py", "main.py")

        try:
            reader = _StreamFrameReader(response)

            while True:
                line = reader.readline()
                if line == "END":
                    break

                if not line.startswith("HASH:"):
                    raise RuntimeError("Unexpected OTA stream frame: " + line)
                expected_hash = line[5:]

                file_line = reader.readline()
                if not file_line.startswith("FILE:"):
                    raise RuntimeError("Expected FILE: line, got: " + file_line)
                rel_path = file_line[5:]

                size_line = reader.readline()
                if not size_line.startswith("SIZE:"):
                    raise RuntimeError("Expected SIZE: line, got: " + size_line)
                size = int(size_line[5:])

                # Resolve staging path before reading content so we can stream
                # directly to disk — no large bytearray needed.
                if rel_path in _ROOT_FILES:
                    target_path = rel_path
                elif rel_path == CONFIG_PATH:
                    target_path = self._config_staging_target()
                else:
                    target_path = self._join(self._staging_root, rel_path)

                self._ensure_dir(self._parent_dir(target_path))

                if rel_path == CONFIG_PATH:
                    # Config is always small (< 2 KB): buffer in memory so we
                    # can verify the hash and apply merge/encrypt before writing.
                    h = _hashlib.sha256()
                    buf = bytearray()
                    for chunk in reader.read_chunks(size):
                        h.update(chunk)
                        buf.extend(chunk)
                    actual_hash = _hex(h.digest())
                    if actual_hash.lower() != expected_hash.lower():
                        self._clear_staging()
                        self._log_error("OTA file hash mismatch", {"path": rel_path})
                        raise ValueError("Hash mismatch for " + rel_path)
                    content = self._merge_config_payload(bytes(buf), update_info.version)
                    buf = None
                    atomic_write_bytes(self._fs, target_path, content)
                    self._log_info("OTA file written to staging", {"path": rel_path, "bytes": len(content)})
                    content = None
                    config_staged = True
                else:
                    # Stream directly to disk chunk-by-chunk — the maximum
                    # in-RAM data is one 512-byte chunk + 32-byte hash state.
                    # This avoids the large contiguous allocation that OOM'd.
                    tmp_path = target_path + ".ota_tmp"
                    h_reader = _HashingChunkReader(reader, size, _hashlib)
                    try:
                        self._fs.write_chunks(tmp_path, h_reader)
                    except Exception:
                        if self._fs.exists(tmp_path):
                            try:
                                self._fs.remove(tmp_path)
                            except Exception:
                                pass
                        raise
                    actual_hash = _hex(h_reader.digest)
                    if actual_hash.lower() != expected_hash.lower():
                        self._fs.remove(tmp_path)
                        self._clear_staging()
                        self._log_error("OTA file hash mismatch", {"path": rel_path})
                        raise ValueError("Hash mismatch for " + rel_path)
                    self._fs.rename(tmp_path, target_path)
                    self._log_info("OTA file written to staging", {"path": rel_path, "bytes": size})

                file_count += 1

                if _gc is not None:
                    _gc.collect()

        finally:
            response.close()

        if file_count == 0:
            self._clear_staging()
            raise RuntimeError("OTA stream contained no files")

        return config_staged

    def _auth_headers(self):
        return {
            "X-Device-ID": self._config.device_id,
            "X-Api-Key": self._config.api_key,
            "X-Platform": self._platform,
        }

    def _flush_logs(self) -> None:
        """Temporarily resume uplink, flush buffered logs, then re-pause."""
        if self._logger is None or not hasattr(self._logger, "flush"):
            return
        if hasattr(self._logger, "resume_uplink"):
            self._logger.resume_uplink()
        try:
            self._logger.flush("ota")
        except Exception:
            pass  # best-effort; don't let a log failure abort OTA
        finally:
            if hasattr(self._logger, "pause_uplink"):
                self._logger.pause_uplink()

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
