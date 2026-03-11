from edge.shared.app.config import Config
from edge.shared.app.device_control import DeviceControlClient
from edge.shared.tests.mocks.mock_http_client import MockHttpClient
from edge.shared.tests.mocks.mock_filesystem import MockFileSystem


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

    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/devices/modules/package?module_id=temp-sensor&version=2.0.0",
        200,
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
    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/devices/modules/package?module_id=temp-sensor&version=2.0.0",
        200,
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

    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/devices/modules/package?module_id=temp-sensor&version=2.0.0",
        200,
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
    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/devices/modules/package?module_id=m1&version=1.0.0",
        200,
        c1,
    )
    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/devices/modules/package?module_id=m2&version=1.0.0",
        200,
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
    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/devices/modules/package?module_id=m-single&version=2.0.0",
        200,
        c1,
    )

    result = client.ensure_assigned_modules_present(
        {"module_id": "m-single", "version": "2.0.0", "package_hash": "sha256:" + h1}
    )

    assert result == {"checked": 1, "ready": 1}