import pytest

from edge.shared.app.config import Config
from edge.shared.tests.mocks.mock_filesystem import MockFileSystem


def test_load_valid_config():
    fs = MockFileSystem()
    fs.write_text(
        "config.json",
        """
        {
          "device_id": "esp32-001",
          "api_url": "http://localhost:8000",
          "api_key": "key",
          "wifi_ssid": "ssid",
          "wifi_password": "pass",
          "heartbeat_interval_ms": 5000,
          "max_boot_attempts": 3
        }
        """,
    )

    config = Config.load(fs)

    assert config.device_id == "esp32-001"
    assert config.api_url == "http://localhost:8000"
    assert config.max_boot_attempts == 3


def test_load_missing_field_raises():
    fs = MockFileSystem()
    fs.write_text(
        "config.json",
        """
        {
          "device_id": "esp32-001",
          "api_url": "http://localhost:8000"
        }
        """,
    )

    with pytest.raises(ValueError):
        Config.load(fs)


def test_load_invalid_json_raises():
    fs = MockFileSystem()
    fs.write_text("config.json", "not-json")

    with pytest.raises(Exception):
        Config.load(fs)
