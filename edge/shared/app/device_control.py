import json

from edge.shared.app.safe_io import atomic_write_text

from edge.shared.app.endpoints import (
    DEV_COMMAND_NEXT_PATH,
    DEV_COMMAND_RESULT_PATH_TEMPLATE,
    MODULE_ASSIGNMENT_PATH,
    MODULE_PACKAGE_PATH,
    MODULE_PREFETCH_PATH,
    MODULE_RESULTS_PATH,
    MODULE_STATUS_PATH,
)


class DeviceControlClient:
    def __init__(self, http, config, fs=None, logger=None, modules_root="modules_cache"):
        self._http = http
        self._config = config
        self._fs = fs
        self._logger = logger
        self._modules_root = modules_root

    def get_next_dev_command(self, last_revision_hash=None):
        url = self._with_query(self._config.api_url + DEV_COMMAND_NEXT_PATH, "last_revision_hash", last_revision_hash)
        response = self._http.get(url, headers=self._auth_headers())
        if response.status_code == 204:
            return None
        if response.status_code != 200:
            self._log_warn("Dev command poll failed", {"status_code": response.status_code})
            return None
        return self._parse_json(response.text)

    def report_dev_command_result(self, command_id, payload):
        path = DEV_COMMAND_RESULT_PATH_TEMPLATE.replace("{commandId}", str(command_id))
        url = self._config.api_url + path
        response = self._http.post(url, payload, headers=self._auth_headers())
        return response.status_code in (200, 201, 202)

    def get_module_assignment(self, last_assignment_hash=None):
        url = self._with_query(self._config.api_url + MODULE_ASSIGNMENT_PATH, "last_assignment_hash", last_assignment_hash)
        response = self._http.get(url, headers=self._auth_headers())
        if response.status_code == 204:
            return None
        if response.status_code != 200:
            self._log_warn("Module assignment poll failed", {"status_code": response.status_code})
            return None
        return self._parse_json(response.text)

    def download_module_package(self, module_id, version, expected_hash=None):
        """Stream the package to flash in small chunks, hashing as it arrives.

        The package is never held in RAM as a whole: on a fragmented MicroPython
        heap even a ~10 KB contiguous buffer can fail to allocate.
        """
        if self._fs is None:
            self._log_warn("Module filesystem unavailable", {"module_id": module_id, "version": version})
            return False

        url = self._config.api_url + MODULE_PACKAGE_PATH + "?module_id=" + str(module_id) + "&version=" + str(version)
        package_path = self._module_package_path(module_id, version)
        tmp_path = package_path + ".tmp"
        hash_path = package_path + _HASH_SUFFIX
        parent = self._parent_dir(package_path)
        if parent and not self._fs.exists(parent):
            self._fs.makedirs(parent)

        _collect_garbage()
        hasher = _sha256()
        try:
            response = self._http.get_stream(url, headers=self._auth_headers())
        except Exception as exc:
            self._log_warn("Module package download failed", {"error": str(exc), "module_id": module_id})
            return False
        try:
            if response.status_code != 200:
                self._log_warn("Module package download failed", {"status_code": response.status_code, "module_id": module_id})
                return False
            self._fs.write_chunks(tmp_path, _hashed_chunks(response, hasher))
        except Exception:
            _remove_file(self._fs, tmp_path)
            raise
        finally:
            response.close()

        digest = _hex(hasher.digest())
        expected = _normalize_hash(expected_hash)
        if expected and digest != expected:
            _remove_file(self._fs, tmp_path)
            self._log_warn("Downloaded module hash mismatch", {"module_id": module_id, "version": version})
            return False

        # Drop the stale hash first: if power fails before the new one is written,
        # the next check falls back to hashing the package itself.
        _remove_file(self._fs, hash_path)
        _remove_file(self._fs, package_path)
        self._fs.rename(tmp_path, package_path)
        atomic_write_text(self._fs, hash_path, digest)
        return True

    def prefetch_server_code(self, modules):
        """Fire-and-forget: ask server to pre-compute variables for upcoming modules."""
        url = self._config.api_url + MODULE_PREFETCH_PATH
        payload = {"modules": modules}
        self._log_info(
            "Sending module prefetch",
            {
                "url": url,
                "module_count": len(modules) if isinstance(modules, list) else 0,
            },
        )
        response = self._http.post(url, payload, headers=self._auth_headers())
        ok = response.status_code in (200, 201, 202)
        if ok:
            self._log_info("Module prefetch accepted", {"status_code": response.status_code})
        else:
            self._log_warn("Module prefetch request failed", {"status_code": response.status_code})
        return ok

    def report_module_result(self, payload):
        url = self._config.api_url + MODULE_RESULTS_PATH
        response = self._http.post(url, payload, headers=self._auth_headers())
        return response.status_code in (200, 201, 202)

    def report_module_status(self, payload):
        url = self._config.api_url + MODULE_STATUS_PATH
        response = self._http.post(url, payload, headers=self._auth_headers())
        return response.status_code in (200, 201, 202)

    def ensure_assigned_modules_present(self, assignment_payload):
        modules = []
        if not assignment_payload:
            return {"checked": 0, "ready": 0}

        if isinstance(assignment_payload, dict) and isinstance(assignment_payload.get("modules"), list):
            modules = assignment_payload.get("modules") or []
        elif isinstance(assignment_payload, dict) and assignment_payload.get("module_id"):
            modules = [assignment_payload]

        checked = 0
        ready = 0
        for module in modules:
            module_id = module.get("module_id")
            version = module.get("version")
            if not module_id or not version:
                continue
            checked += 1
            try:
                if self.ensure_module_present(module_id, version, module.get("package_hash")):
                    ready += 1
            except Exception as exc:
                # Includes MemoryError: one failed download must not take down the control loop.
                self._log_warn(
                    "Module package fetch failed",
                    {"module_id": module_id, "version": version, "error": str(exc) or type(exc).__name__},
                )

        return {"checked": checked, "ready": ready}

    def ensure_module_present(self, module_id, version, expected_hash=None):
        if self._fs is None:
            self._log_warn("Module filesystem unavailable", {"module_id": module_id, "version": version})
            return False

        package_path = self._module_package_path(module_id, version)
        if self._fs.exists(package_path):
            if self._cached_hash_matches(package_path, expected_hash):
                return True
            self._log_warn("Cached module hash mismatch; redownloading", {"module_id": module_id, "version": version})

        return self.download_module_package(module_id, version, expected_hash)

    def _cached_hash_matches(self, package_path, expected_hash):
        expected = _normalize_hash(expected_hash)
        if not expected:
            return True
        if self._fs is None:
            return False
        hash_path = package_path + _HASH_SUFFIX
        if self._fs.exists(hash_path):
            return self._fs.read_text(hash_path).strip().lower() == expected
        # Packages cached before hash files existed: verify once, then record the hash.
        _collect_garbage()
        if self._digest_bytes(self._fs.read_bytes(package_path)) != expected:
            return False
        atomic_write_text(self._fs, hash_path, expected)
        return True

    def get_cached_module_package(self, module_id, version):
        if self._fs is None:
            return None
        package_path = self._module_package_path(module_id, version)
        if not self._fs.exists(package_path):
            return None
        return self._fs.read_bytes(package_path)

    @staticmethod
    def should_execute_dev_command(command, last_revision_hash):
        if not command:
            return False
        if bool(command.get("forceRerun", False)):
            return True
        return command.get("revision_hash") != last_revision_hash

    def _auth_headers(self):
        return {
            "X-Device-ID": self._config.device_id,
            "X-Api-Key": self._config.api_key,
        }

    @staticmethod
    def _with_query(base_url, key, value):
        if value is None:
            return base_url
        return base_url + "?" + key + "=" + str(value)

    @staticmethod
    def _parse_json(text):
        try:
            return json.loads(text) if text else {}
        except Exception:
            return {}

    @staticmethod
    def _digest_bytes(data):
        hasher = _sha256()
        hasher.update(data)
        return _hex(hasher.digest())

    def _module_package_path(self, module_id, version):
        return self._modules_root + "/" + str(module_id) + "/" + str(version) + ".pkg"

    @staticmethod
    def _parent_dir(path):
        if "/" not in path:
            return ""
        return path.rsplit("/", 1)[0]

    def _log_warn(self, message, context=None):
        if self._logger is not None:
            self._logger.warn(message, context)

    def _log_info(self, message, context=None):
        if self._logger is not None:
            self._logger.info(message, context)


_HASH_SUFFIX = ".sha256"
_PACKAGE_CHUNK_SIZE = 512


def _sha256():
    try:
        import uhashlib as hashlib  # pyright: ignore[reportMissingImports]
    except ImportError:  # pragma: no cover - desktop fallback
        import hashlib
    return hashlib.sha256()


def _hex(digest):
    return "".join("{:02x}".format(byte) for byte in digest)


def _normalize_hash(expected_hash):
    if not expected_hash:
        return ""
    expected = str(expected_hash)
    if expected.startswith("sha256:"):
        expected = expected.split(":", 1)[1]
    return expected.strip().lower()


def _hashed_chunks(response, hasher):
    # One reused buffer: no per-chunk allocations on the device heap.
    mv = memoryview(bytearray(_PACKAGE_CHUNK_SIZE))
    while True:
        n = response.readinto(mv)
        if not n:
            return
        hasher.update(mv[:n])
        yield mv[:n]


def _remove_file(fs, path):
    if fs.exists(path) and not fs.is_dir(path):
        fs.remove(path)


def _collect_garbage():
    try:
        import gc
        gc.collect()
    except Exception:  # pragma: no cover - gc is always present on supported ports
        pass