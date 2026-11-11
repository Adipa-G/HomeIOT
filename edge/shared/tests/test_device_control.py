from edge.shared.app.config import Config
from edge.shared.app.device_control import DeviceControlClient
from edge.shared.tests.mocks.mock_http_client import MockHttpClient
from edge.shared.tests.mocks.mock_filesystem import MockFileSystem


PACKAGE_URL = "http://localhost:8000/api/devices/modules/package?module_id=temp-sensor&version=2.0.0"
PACKAGE_PATH = "modules_cache/temp-sensor/2.0.0.pkg"


def _config():
    return Config(
        device_id="esp32-001",
        api_url="http://localhost:8000",
        api_key="secret",
        wifi_ssid="ssid",
        wifi_password="pass",
        heartbeat_interval_ms=1000,
        max_boot_attempts=3,
        current_version="1.0.0",
    )


def test_get_next_dev_command_includes_auth_headers():
    http = MockHttpClient()
    client = DeviceControlClient(http=http, config=_config())
    http.add_json_response(
        "GET",
        "http://localhost:8000/api/devices/dev-commands/next?last_revision_hash=abc",
        200,
        {"command_id": "cmd-1", "revision_hash": "def", "forceRerun": False},
    )

    command = client.get_next_dev_command(last_revision_hash="abc")

    assert command["command_id"] == "cmd-1"
    method, _, _, headers = http.calls[0]
    assert method == "GET"
    assert headers["X-Device-ID"] == "esp32-001"
    assert headers["X-Api-Key"] == "secret"


def test_report_dev_command_result_posts_to_templated_path():
    http = MockHttpClient()
    client = DeviceControlClient(http=http, config=_config())

    ok = client.report_dev_command_result("cmd-1", {"status": "success"})

    assert ok is True
    method, url, data, _ = http.calls[0]
    assert method == "POST"
    assert url == "http://localhost:8000/api/devices/dev-commands/cmd-1/result"
    assert data["status"] == "success"


def test_get_module_assignment_and_module_result_flow():
    http = MockHttpClient()
    client = DeviceControlClient(http=http, config=_config())
    http.add_json_response(
        "GET",
        "http://localhost:8000/api/devices/modules/assignment?last_assignment_hash=old",
        200,
        {"assignment_hash": "new", "modules": []},
    )

    assignment = client.get_module_assignment(last_assignment_hash="old")
    posted = client.report_module_result({"module_id": "m1", "status": "success"})

    assert assignment["assignment_hash"] == "new"
    assert posted is True


def test_execute_on_change_semantics():
    same = {"revision_hash": "abc", "forceRerun": False}
    rerun = {"revision_hash": "abc", "forceRerun": True}
    changed = {"revision_hash": "def", "forceRerun": False}

    assert DeviceControlClient.should_execute_dev_command(same, "abc") is False
    assert DeviceControlClient.should_execute_dev_command(rerun, "abc") is True
    assert DeviceControlClient.should_execute_dev_command(changed, "abc") is True


def test_ensure_module_present_downloads_when_missing_and_caches():
    http = MockHttpClient()
    fs = MockFileSystem()
    client = DeviceControlClient(http=http, config=_config(), fs=fs)
    module_id = "temp-sensor"
    version = "2.0.0"
    content = b"module-bytes"
    digest = DeviceControlClient._digest_bytes(content)

    http.add_stream_response(
        "http://localhost:8000/api/devices/modules/package?module_id=temp-sensor&version=2.0.0",
        content,
    )

    ok = client.ensure_module_present(module_id, version, "sha256:" + digest)

    assert ok is True
    cached = client.get_cached_module_package(module_id, version)
    assert cached == content


def test_ensure_module_present_redownloads_on_hash_mismatch():
    http = MockHttpClient()
    fs = MockFileSystem()
    client = DeviceControlClient(http=http, config=_config(), fs=fs)
    module_id = "temp-sensor"
    version = "2.0.0"

    bad_content = b"stale"
    good_content = b"fresh"
    good_hash = DeviceControlClient._digest_bytes(good_content)

    fs.write_bytes("modules_cache/temp-sensor/2.0.0.pkg", bad_content)
    http.add_stream_response(
        "http://localhost:8000/api/devices/modules/package?module_id=temp-sensor&version=2.0.0",
        good_content,
    )

    ok = client.ensure_module_present(module_id, version, "sha256:" + good_hash)

    assert ok is True
    assert client.get_cached_module_package(module_id, version) == good_content


def test_ensure_module_present_returns_false_on_download_hash_mismatch():
    http = MockHttpClient()
    fs = MockFileSystem()
    client = DeviceControlClient(http=http, config=_config(), fs=fs)
    module_id = "temp-sensor"
    version = "2.0.0"

    http.add_stream_response(
        "http://localhost:8000/api/devices/modules/package?module_id=temp-sensor&version=2.0.0",
        b"wrong-content",
    )

    ok = client.ensure_module_present(module_id, version, "sha256:deadbeef")

    assert ok is False
    assert client.get_cached_module_package(module_id, version) is None


def test_ensure_assigned_modules_present_for_modules_list():
    http = MockHttpClient()
    fs = MockFileSystem()
    client = DeviceControlClient(http=http, config=_config(), fs=fs)

    c1 = b"module-a"
    c2 = b"module-b"
    h1 = DeviceControlClient._digest_bytes(c1)
    h2 = DeviceControlClient._digest_bytes(c2)
    http.add_stream_response(
        "http://localhost:8000/api/devices/modules/package?module_id=m1&version=1.0.0",
        c1,
    )
    http.add_stream_response(
        "http://localhost:8000/api/devices/modules/package?module_id=m2&version=1.0.0",
        c2,
    )

    result = client.ensure_assigned_modules_present(
        {
            "assignment_hash": "a1",
            "modules": [
                {"module_id": "m1", "version": "1.0.0", "package_hash": "sha256:" + h1},
                {"module_id": "m2", "version": "1.0.0", "package_hash": "sha256:" + h2},
            ],
        }
    )

    assert result == {"checked": 2, "ready": 2}


def test_ensure_assigned_modules_present_for_single_module_shape():
    http = MockHttpClient()
    fs = MockFileSystem()
    client = DeviceControlClient(http=http, config=_config(), fs=fs)

    c1 = b"module-single"
    h1 = DeviceControlClient._digest_bytes(c1)
    http.add_stream_response(
        "http://localhost:8000/api/devices/modules/package?module_id=m-single&version=2.0.0",
        c1,
    )

    result = client.ensure_assigned_modules_present(
        {"module_id": "m-single", "version": "2.0.0", "package_hash": "sha256:" + h1}
    )

    assert result == {"checked": 1, "ready": 1}

class _Logger:
    def __init__(self):
        self.warnings = []

    def info(self, message, context=None):
        pass

    def warn(self, message, context=None):
        self.warnings.append((message, context or {}))


def test_module_package_is_streamed_and_hash_recorded():
    http = MockHttpClient()
    fs = MockFileSystem()
    client = DeviceControlClient(http=http, config=_config(), fs=fs)
    content = b"x" * 5000
    digest = DeviceControlClient._digest_bytes(content)
    http.add_stream_response(PACKAGE_URL, content)

    assert client.ensure_module_present("temp-sensor", "2.0.0", "sha256:" + digest.upper()) is True

    assert [call[0] for call in http.calls] == ["GET_STREAM"]
    assert fs.read_bytes(PACKAGE_PATH) == content
    assert fs.read_text(PACKAGE_PATH + ".sha256") == digest
    assert not fs.exists(PACKAGE_PATH + ".tmp")


def test_cached_package_checked_against_hash_file_without_reading_package():
    http = MockHttpClient()
    fs = MockFileSystem()
    client = DeviceControlClient(http=http, config=_config(), fs=fs)
    fs.write_bytes(PACKAGE_PATH, b"anything")
    fs.write_text(PACKAGE_PATH + ".sha256", "abc123")

    real_read_bytes = fs.read_bytes

    def fail_package_read(path):
        if path == PACKAGE_PATH:
            raise AssertionError("package should not be read")
        return real_read_bytes(path)

    fs.read_bytes = fail_package_read

    assert client.ensure_module_present("temp-sensor", "2.0.0", "sha256:ABC123") is True
    assert http.calls == []


def test_cached_package_without_hash_file_is_verified_once_and_hash_recorded():
    http = MockHttpClient()
    fs = MockFileSystem()
    client = DeviceControlClient(http=http, config=_config(), fs=fs)
    content = b"legacy-cached"
    digest = DeviceControlClient._digest_bytes(content)
    fs.write_bytes(PACKAGE_PATH, content)

    assert client.ensure_module_present("temp-sensor", "2.0.0", "sha256:" + digest) is True
    assert http.calls == []
    assert fs.read_text(PACKAGE_PATH + ".sha256") == digest


def test_stale_hash_file_replaced_on_redownload():
    http = MockHttpClient()
    fs = MockFileSystem()
    client = DeviceControlClient(http=http, config=_config(), fs=fs)
    fs.write_bytes(PACKAGE_PATH, b"old")
    fs.write_text(PACKAGE_PATH + ".sha256", DeviceControlClient._digest_bytes(b"old"))
    content = b"new"
    digest = DeviceControlClient._digest_bytes(content)
    http.add_stream_response(PACKAGE_URL, content)

    assert client.ensure_module_present("temp-sensor", "2.0.0", "sha256:" + digest) is True
    assert fs.read_bytes(PACKAGE_PATH) == content
    assert fs.read_text(PACKAGE_PATH + ".sha256") == digest


def test_download_hash_mismatch_keeps_existing_package_and_removes_partial_file():
    http = MockHttpClient()
    fs = MockFileSystem()
    client = DeviceControlClient(http=http, config=_config(), fs=fs)
    fs.write_bytes(PACKAGE_PATH, b"old")
    http.add_stream_response(PACKAGE_URL, b"corrupt")

    assert client.ensure_module_present("temp-sensor", "2.0.0", "sha256:deadbeef") is False
    assert fs.read_bytes(PACKAGE_PATH) == b"old"
    assert not fs.exists(PACKAGE_PATH + ".tmp")
    assert not fs.exists(PACKAGE_PATH + ".sha256")


def test_download_returns_false_on_http_error():
    http = MockHttpClient()
    fs = MockFileSystem()
    client = DeviceControlClient(http=http, config=_config(), fs=fs)
    http.add_stream_response(PACKAGE_URL, b"", status_code=404)

    assert client.ensure_module_present("temp-sensor", "2.0.0", "sha256:deadbeef") is False
    assert not fs.exists(PACKAGE_PATH)


def test_download_returns_false_when_stream_cannot_open():
    http = MockHttpClient()
    fs = MockFileSystem()
    logger = _Logger()
    client = DeviceControlClient(http=http, config=_config(), fs=fs, logger=logger)

    def raise_os_error(url, headers=None):
        raise OSError("HTTP 500")

    http.get_stream = raise_os_error

    assert client.ensure_module_present("temp-sensor", "2.0.0") is False
    assert logger.warnings[0][0] == "Module package download failed"


def test_memory_error_during_download_is_logged_not_raised():
    http = MockHttpClient()
    fs = MockFileSystem()
    logger = _Logger()
    client = DeviceControlClient(http=http, config=_config(), fs=fs, logger=logger)
    http.add_stream_response(PACKAGE_URL, b"module-bytes")
    http.add_stream_response(
        "http://localhost:8000/api/devices/modules/package?module_id=other&version=1.0.0", b"other"
    )
    real_write_chunks = fs.write_chunks

    def write_chunks(path, chunks):
        if path.startswith("modules_cache/temp-sensor/"):
            fs.write_bytes(path, b"partial")
            raise MemoryError("memory allocation failed, allocating 4865 bytes")
        real_write_chunks(path, chunks)

    fs.write_chunks = write_chunks

    result = client.ensure_assigned_modules_present(
        {
            "modules": [
                {"module_id": "temp-sensor", "version": "2.0.0"},
                {"module_id": "other", "version": "1.0.0"},
            ]
        }
    )

    assert result == {"checked": 2, "ready": 1}
    assert not fs.exists(PACKAGE_PATH + ".tmp")
    message, context = logger.warnings[0]
    assert message == "Module package fetch failed"
    assert context["module_id"] == "temp-sensor"
    assert "4865" in context["error"]
