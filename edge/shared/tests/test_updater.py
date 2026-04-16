import json

from edge.shared.app.secret_crypto import encrypt_secret

import pytest

from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import Config
from edge.shared.app.updater import UpdateInfo, Updater
from edge.shared.tests.mocks.mock_filesystem import MockFileSystem
from edge.shared.tests.mocks.mock_http_client import MockHttpClient
from edge.shared.tests.mocks.mock_system import MockSystem


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


def test_check_returns_none_when_no_update():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    http.add_json_response(
        "GET",
        "http://localhost:8000/api/ota/check?version=1.0.0",
        200,
        {"available": False},
    )

    update = updater.check()

    assert update is None
    assert http.calls[0][1] == "http://localhost:8000/api/ota/check?version=1.0.0"
    assert http.calls[0][3]["X-Platform"] == "esp32"


def test_apply_downloads_and_swaps_version():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    fs.write_bytes("app/main.py", b"old-version")
    fs.write_text(
        "config.json",
        """
        {"device_id":"esp32-001","api_url":"http://localhost:8000","api_key":"old-secret","wifi_ssid":"ssid","wifi_password":"old-pass","heartbeat_interval_ms":1000,"max_boot_attempts":3,"current_version":"1.0.0"}
        """.strip(),
    )

    new_file = b"print('new-version')"
    expected_hash = updater._digest_bytes(new_file)
    # Staged config: placeholders for device secrets (should be preserved from active),
    # real values for non-secret fields (should be taken from the new release),
    # and a real api_url (should override the active value).
    new_config = b"{\"device_id\":\"replace-with-device-id\",\"api_url\":\"replace-with-api-url\",\"api_key\":\"replace-with-device-api-key\",\"wifi_ssid\":\"replace-with-ssid\",\"wifi_password\":\"replace-with-password\",\"heartbeat_interval_ms\":2000,\"max_boot_attempts\":4,\"current_version\":\"1.1.0\"}"
    expected_config_hash = updater._digest_bytes(new_config)

    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/ota/file?version=1.1.0&path=main.py",
        200,
        new_file,
    )
    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/ota/file?version=1.1.0&path=config.json",
        200,
        new_config,
    )

    updater.apply(
        UpdateInfo(
            available=True,
            version="1.1.0",
            manifest=[
                {"path": "main.py", "hash": expected_hash, "size": len(new_file)},
                {"path": "config.json", "hash": expected_config_hash, "size": len(new_config)},
            ],
        )
    )

    assert fs.read_bytes("app/main.py") == new_file
    assert fs.read_bytes("app_prev/main.py") == b"old-version"
    merged_config = json.loads(fs.read_text("config.json"))
    assert merged_config["device_id"] == "esp32-001"            # placeholder → preserved from active
    assert merged_config["api_key"] == "old-secret"              # placeholder → preserved from active
    assert merged_config["wifi_password"] == "old-pass"          # placeholder → preserved from active
    assert merged_config["api_url"] == "http://localhost:8000"   # placeholder → preserved from active
    assert merged_config["heartbeat_interval_ms"] == 2000
    assert merged_config["max_boot_attempts"] == 4
    assert merged_config["current_version"] == "1.1.0"
    assert fs.read_text("config_prev.json").startswith("{\"device_id\":\"esp32-001\"")
    assert system.reset_calls == 1


def test_apply_preserves_enc_credentials_when_absent_from_staged():
    """Devices using encrypted credentials (api_key_enc / wifi_password_enc) must not
    lose those fields after OTA — the artifact template never contains enc objects."""
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    # Use properly encrypted fixtures so staged config validation (Config.load) can decrypt them.
    # Config.load tries device_id as binding first.
    device_id = "esp32-001"
    api_key_enc = encrypt_secret("real-api-key", device_id, "api_key")
    wifi_password_enc = encrypt_secret("real-wifi-pass", device_id, "wifi_password")

    fs.write_bytes("app/main.py", b"old-version")
    fs.write_text(
        "config.json",
        json.dumps({
            "device_id": device_id,
            "api_url": "http://localhost:8000",
            "api_key_enc": api_key_enc,
            "wifi_ssid": "ssid",
            "wifi_password_enc": wifi_password_enc,
            "heartbeat_interval_ms": 1000,
            "max_boot_attempts": 3,
            "current_version": "1.0.0",
        }, separators=(",", ":")),
    )

    new_file = b"print('new-version')"
    # Staged config has no api_key_enc / wifi_password_enc — they must be copied from active.
    new_config = json.dumps({
        "device_id": "replace-with-device-id",
        "api_url": "replace-with-api-url",
        "api_key": "replace-with-device-api-key",
        "wifi_ssid": "replace-with-ssid",
        "wifi_password": "replace-with-password",
        "heartbeat_interval_ms": 2000,
        "max_boot_attempts": 4,
        "current_version": "1.1.0",
    }, separators=(",", ":")).encode("utf-8")

    http.add_bytes_response("GET", "http://localhost:8000/api/ota/file?version=1.1.0&path=main.py", 200, new_file)
    http.add_bytes_response("GET", "http://localhost:8000/api/ota/file?version=1.1.0&path=config.json", 200, new_config)

    updater.apply(
        UpdateInfo(
            available=True,
            version="1.1.0",
            manifest=[
                {"path": "main.py", "hash": updater._digest_bytes(new_file), "size": len(new_file)},
                {"path": "config.json", "hash": updater._digest_bytes(new_config), "size": len(new_config)},
            ],
        )
    )

    merged_config = json.loads(fs.read_text("config.json"))
    assert merged_config["device_id"] == device_id
    assert merged_config["api_url"] == "http://localhost:8000"
    assert "api_key" not in merged_config                          # placeholder removed, enc used instead
    assert merged_config["api_key_enc"] == api_key_enc             # absent from staged → preserved from active
    assert merged_config["wifi_password_enc"] == wifi_password_enc # absent from staged → preserved from active
    assert "wifi_password" not in merged_config                    # placeholder removed, enc used instead
    assert merged_config["heartbeat_interval_ms"] == 2000
    assert merged_config["current_version"] == "1.1.0"


def test_apply_encrypts_new_plaintext_credentials_from_release():
    """If a release ships a real plaintext api_key or wifi_password (key rotation),
    the device must encrypt it before writing — never store secrets as plaintext."""
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    device_id = "esp32-001"
    old_api_key_enc = encrypt_secret("old-api-key", device_id, "api_key")
    old_wifi_password_enc = encrypt_secret("old-wifi-pass", device_id, "wifi_password")

    fs.write_bytes("app/main.py", b"old-version")
    fs.write_text(
        "config.json",
        json.dumps({
            "device_id": device_id,
            "api_url": "http://localhost:8000",
            "api_key_enc": old_api_key_enc,
            "wifi_ssid": "ssid",
            "wifi_password_enc": old_wifi_password_enc,
            "heartbeat_interval_ms": 1000,
            "max_boot_attempts": 3,
            "current_version": "1.0.0",
        }, separators=(",", ":")),
    )

    new_file = b"print('new-version')"
    # Release ships a new plaintext api_key (key rotation) — device must encrypt it.
    new_config = json.dumps({
        "device_id": "replace-with-device-id",
        "api_url": "replace-with-api-url",
        "api_key": "rotated-api-key",
        "wifi_ssid": "replace-with-ssid",
        "wifi_password": "replace-with-password",
        "heartbeat_interval_ms": 2000,
        "max_boot_attempts": 4,
        "current_version": "1.1.0",
    }, separators=(",", ":")).encode("utf-8")

    http.add_bytes_response("GET", "http://localhost:8000/api/ota/file?version=1.1.0&path=main.py", 200, new_file)
    http.add_bytes_response("GET", "http://localhost:8000/api/ota/file?version=1.1.0&path=config.json", 200, new_config)

    updater.apply(
        UpdateInfo(
            available=True,
            version="1.1.0",
            manifest=[
                {"path": "main.py", "hash": updater._digest_bytes(new_file), "size": len(new_file)},
                {"path": "config.json", "hash": updater._digest_bytes(new_config), "size": len(new_config)},
            ],
        )
    )

    merged_config = json.loads(fs.read_text("config.json"))
    assert "api_key" not in merged_config                   # plaintext must never be stored
    assert "api_key_enc" in merged_config                   # must be encrypted
    assert merged_config["api_key_enc"] != old_api_key_enc  # new key, new enc object
    # wifi_password was a placeholder → old enc preserved
    assert "wifi_password" not in merged_config
    assert merged_config["wifi_password_enc"] == old_wifi_password_enc
    assert merged_config["current_version"] == "1.1.0"


def test_apply_raises_on_hash_mismatch_and_cleans_staging():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/ota/file?version=1.1.0&path=main.py",
        200,
        b"bad-content",
    )

    with pytest.raises(ValueError):
        updater.apply(
            UpdateInfo(
                available=True,
                version="1.1.0",
                manifest=[{"path": "main.py", "hash": "1234", "size": 11}],
            )
        )

    assert not fs.exists("app_staging")


def test_apply_raises_on_invalid_config_and_cleans_staging():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    fs.write_text(
        "config.json",
        """
        {"device_id":"esp32-001","api_url":"http://localhost:8000","api_key":"old-secret","wifi_ssid":"ssid","wifi_password":"old-pass","heartbeat_interval_ms":1000,"max_boot_attempts":3,"current_version":"1.0.0"}
        """.strip(),
    )

    new_file = b"print('new-version')"
    expected_hash = updater._digest_bytes(new_file)
    invalid_config = b"{\"device_id\":\"esp32-001\",\"api_url\":\"http://localhost:8000\"}"
    expected_config_hash = updater._digest_bytes(invalid_config)

    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/ota/file?version=1.1.0&path=main.py",
        200,
        new_file,
    )
    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/ota/file?version=1.1.0&path=config.json",
        200,
        invalid_config,
    )

    with pytest.raises(ValueError):
        updater.apply(
            UpdateInfo(
                available=True,
                version="1.1.0",
                manifest=[
                    {"path": "main.py", "hash": expected_hash, "size": len(new_file)},
                    {"path": "config.json", "hash": expected_config_hash, "size": len(invalid_config)},
                ],
            )
        )

    assert fs.read_text("config.json").startswith("{\"device_id\":\"esp32-001\"")
    assert not fs.exists("config_staging.json")
    assert not fs.exists("app_staging")


def test_download_retries_on_failure():
    """_download_file retries on exception and succeeds on subsequent attempt."""
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    new_file = b"print('retried')"
    expected_hash = updater._digest_bytes(new_file)

    # Track call count to simulate transient failure
    call_count = [0]
    original_get = http.get

    def flaky_get(url, headers=None):
        call_count[0] += 1
        if call_count[0] == 1 and "file" in url:
            raise OSError("socket exhaustion")
        return original_get(url, headers)

    http.get = flaky_get
    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/ota/file?version=1.1.0&path=main.py",
        200,
        new_file,
    )

    fs.write_text(
        "config.json",
        '{"device_id":"esp32-001","api_url":"http://localhost:8000","api_key":"secret","wifi_ssid":"ssid","wifi_password":"pass","heartbeat_interval_ms":1000,"max_boot_attempts":3,"current_version":"1.0.0"}',
    )

    updater.apply(
        UpdateInfo(
            available=True,
            version="1.1.0",
            manifest=[{"path": "main.py", "hash": expected_hash, "size": len(new_file)}],
        )
    )

    assert call_count[0] == 2  # first failed, second succeeded
    assert system.reset_calls == 1


def test_apply_resumes_uplink_on_failure():
    """If apply() raises, logger.resume_uplink() must still be called."""
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)

    class FakeLogger:
        def __init__(self):
            self.paused = False
            self.resumed = False
        def pause_uplink(self):
            self.paused = True
        def resume_uplink(self):
            self.resumed = True
        def info(self, msg, ctx=None):
            pass
        def warn(self, msg, ctx=None):
            pass
        def error(self, msg, ctx=None):
            pass

    logger = FakeLogger()
    updater = Updater(fs=fs, http=http, system=system, config=_config(),
                      boot_manager=boot_manager, logger=logger)

    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/ota/file?version=1.1.0&path=main.py",
        200,
        b"bad-content",
    )

    with pytest.raises(ValueError):
        updater.apply(
            UpdateInfo(
                available=True,
                version="1.1.0",
                manifest=[{"path": "main.py", "hash": "0000", "size": 11}],
            )
        )

    assert logger.paused
    assert logger.resumed
