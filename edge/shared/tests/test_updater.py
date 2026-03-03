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
        "http://localhost:8000/api/ota/check",
        200,
        {"available": False},
    )

    update = updater.check()

    assert update is None


def test_apply_downloads_and_swaps_version():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    boot_manager = BootManager(fs=fs, system=system, max_attempts=3)
    updater = Updater(fs=fs, http=http, system=system, config=_config(), boot_manager=boot_manager)

    fs.write_bytes("app/main.py", b"old-version")

    new_file = b"print('new-version')"
    expected_hash = updater._digest_bytes(new_file)

    http.add_bytes_response(
        "GET",
        "http://localhost:8000/api/ota/file?version=1.1.0&path=main.py",
        200,
        new_file,
    )

    updater.apply(
        UpdateInfo(
            available=True,
            version="1.1.0",
            manifest=[{"path": "main.py", "hash": expected_hash, "size": len(new_file)}],
        )
    )

    assert fs.read_bytes("app/main.py") == new_file
    assert fs.read_bytes("app_prev/main.py") == b"old-version"
    assert system.reset_calls == 1


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
