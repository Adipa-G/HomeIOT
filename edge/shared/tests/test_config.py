import json

import pytest

from edge.shared.app.config import Config
from edge.shared.app.secret_crypto import encrypt_secret
from edge.shared.tests.mocks.mock_filesystem import MockFileSystem
from edge.shared.tests.mocks.mock_system import MockSystem


def _write_config(fs: MockFileSystem, payload: dict) -> None:
    fs.write_text("config.json", json.dumps(payload))


def test_load_valid_config():
    fs = MockFileSystem()
    _write_config(
        fs,
        {
            "device_id": "esp32-001",
            "api_url": "http://localhost:8000",
            "api_key": "key",
            "wifi_ssid": "ssid",
            "wifi_password": "pass",
            "heartbeat_interval_ms": 5000,
            "max_boot_attempts": 3,
        },
    )

    config = Config.load(fs)

    assert config.device_id == "esp32-001"
    assert config.api_url == "http://localhost:8000"
    assert config.max_boot_attempts == 3
    assert config.dev_poll_interval_ms == 2000
    assert config.module_assignment_poll_interval_ms == 60000


def test_load_control_polling_config_with_bounds():
    fs = MockFileSystem()
    _write_config(
        fs,
        {
            "device_id": "esp32-001",
            "api_url": "http://localhost:8000",
            "api_key": "key",
            "wifi_ssid": "ssid",
            "wifi_password": "pass",
            "heartbeat_interval_ms": 5000,
            "max_boot_attempts": 3,
            "dev_poll_interval_ms": 100,
            "module_assignment_poll_interval_ms": 500,
        },
    )

    config = Config.load(fs)

    assert config.dev_poll_interval_ms == 500
    assert config.module_assignment_poll_interval_ms == 1000


def test_load_missing_field_raises():
    fs = MockFileSystem()
    _write_config(fs, {"device_id": "esp32-001", "api_url": "http://localhost:8000"})

    with pytest.raises(ValueError):
        Config.load(fs)


def test_load_invalid_json_raises():
    fs = MockFileSystem()
    fs.write_text("config.json", "not-json")

    with pytest.raises(Exception):
        Config.load(fs)


def test_load_encrypted_secrets_with_matching_unique_id():
    fs = MockFileSystem()
    system = MockSystem()
    api_enc = encrypt_secret("key", "mock-device-id", "api_key")
    wifi_enc = encrypt_secret("pass", "mock-device-id", "wifi_password")

    _write_config(
        fs,
        {
            "device_id": "esp32-001",
            "api_url": "http://localhost:8000",
            "wifi_ssid": "ssid",
            "heartbeat_interval_ms": 5000,
            "max_boot_attempts": 3,
            "api_key_enc": api_enc,
            "wifi_password_enc": wifi_enc,
        },
    )

    config = Config.load(fs, system=system)

    assert config.api_key == "key"
    assert config.wifi_password == "pass"


def test_load_encrypted_secret_without_system_raises():
    fs = MockFileSystem()
    api_enc = encrypt_secret("key", "mock-device-id", "api_key")
    _write_config(
        fs,
        {
            "device_id": "esp32-001",
            "api_url": "http://localhost:8000",
            "wifi_ssid": "ssid",
            "heartbeat_interval_ms": 5000,
            "max_boot_attempts": 3,
            "api_key_enc": api_enc,
            "wifi_password": "pass",
        },
    )

    with pytest.raises(ValueError):
        Config.load(fs)


def test_load_encrypted_secret_with_wrong_unique_id_raises():
    fs = MockFileSystem()
    api_enc = encrypt_secret("key", "mock-device-id", "api_key")
    _write_config(
        fs,
        {
            "device_id": "esp32-001",
            "api_url": "http://localhost:8000",
            "wifi_ssid": "ssid",
            "heartbeat_interval_ms": 5000,
            "max_boot_attempts": 3,
            "api_key_enc": api_enc,
            "wifi_password": "pass",
        },
    )

    class WrongSystem(MockSystem):
        def unique_id(self) -> str:
            return "wrong-device-id"

    with pytest.raises(ValueError):
        Config.load(fs, system=WrongSystem())
