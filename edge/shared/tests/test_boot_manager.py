import json

from edge.shared.app.boot_manager import BootManager
from edge.shared.tests.mocks.mock_filesystem import MockFileSystem
from edge.shared.tests.mocks.mock_system import MockSystem


def test_on_boot_creates_and_increments_state():
    fs = MockFileSystem()
    system = MockSystem()
    manager = BootManager(fs=fs, system=system, max_attempts=3)

    state = manager.on_boot()

    assert state["boot_count"] == 1
    persisted = json.loads(fs.read_text("boot_state.json"))
    assert persisted["boot_count"] == 1


def test_mark_success_resets_counter():
    fs = MockFileSystem()
    system = MockSystem()
    manager = BootManager(fs=fs, system=system, max_attempts=3)

    manager.on_boot()
    manager.mark_success()

    state = json.loads(fs.read_text("boot_state.json"))
    assert state["boot_count"] == 0
    assert state["boot_succeeded"] is True
    assert state["pending_app_changed"] is False
    assert state["pending_config_changed"] is False
    assert state["current_version"] == "0.0.0"
    assert state["config_version"] == "0.0.0"


def test_set_new_version_swaps_staging_and_backup():
    fs = MockFileSystem()
    system = MockSystem()
    manager = BootManager(fs=fs, system=system, max_attempts=3)

    manager.on_boot()
    fs.write_bytes("app/main.py", b"old")
    fs.write_bytes("app_staging/main.py", b"new")
    fs.write_text(
        "config.json",
        json.dumps(
            {
                "device_id": "esp32-001",
                "api_url": "http://localhost:8000",
                "api_key": "old-key",
                "wifi_ssid": "ssid",
                "wifi_password": "old-pass",
                "heartbeat_interval_ms": 5000,
                "max_boot_attempts": 3,
                "current_version": "1.0.0",
            }
        ),
    )
    fs.write_text(
        "config_staging.json",
        json.dumps(
            {
                "device_id": "esp32-001",
                "api_url": "http://localhost:8000",
                "api_key": "new-key",
                "wifi_ssid": "ssid",
                "wifi_password": "new-pass",
                "heartbeat_interval_ms": 7000,
                "max_boot_attempts": 4,
                "current_version": "1.2.0",
            }
        ),
    )

    manager.set_new_version("1.2.0")

    assert fs.read_bytes("app/main.py") == b"new"
    assert fs.read_bytes("app_prev/main.py") == b"old"
    assert json.loads(fs.read_text("config.json"))["current_version"] == "1.2.0"
    assert json.loads(fs.read_text("config_prev.json"))["current_version"] == "1.0.0"
    assert not fs.exists("config_staging.json")
    state = json.loads(fs.read_text("boot_state.json"))
    assert state["current_version"] == "1.2.0"
    assert state["config_version"] == "1.2.0"
    assert state["pending_app_changed"] is True
    assert state["pending_config_changed"] is True


def test_set_new_version_with_config_only_keeps_live_app_and_refreshes_backup():
    fs = MockFileSystem()
    system = MockSystem()
    manager = BootManager(fs=fs, system=system, max_attempts=3)

    manager.on_boot()
    fs.write_bytes("app/main.py", b"stable-app")
    fs.write_text(
        "config.json",
        json.dumps(
            {
                "device_id": "esp32-001",
                "api_url": "http://localhost:8000",
                "api_key": "old-key",
                "wifi_ssid": "ssid",
                "wifi_password": "old-pass",
                "heartbeat_interval_ms": 5000,
                "max_boot_attempts": 3,
                "current_version": "1.0.0",
            }
        ),
    )
    fs.write_text(
        "config_staging.json",
        json.dumps(
            {
                "device_id": "esp32-001",
                "api_url": "http://localhost:8000",
                "api_key": "new-key",
                "wifi_ssid": "ssid",
                "wifi_password": "new-pass",
                "heartbeat_interval_ms": 7000,
                "max_boot_attempts": 4,
                "current_version": "1.0.1",
            }
        ),
    )

    manager.set_new_version("1.0.1")

    assert fs.read_bytes("app/main.py") == b"stable-app"
    assert not fs.exists("app_prev")
    assert json.loads(fs.read_text("config.json"))["current_version"] == "1.0.1"
    assert json.loads(fs.read_text("config_prev.json"))["current_version"] == "1.0.0"
    state = json.loads(fs.read_text("boot_state.json"))
    assert state["current_version"] == "0.0.0"
    assert state["config_version"] == "1.0.1"
    assert state["pending_app_changed"] is False
    assert state["pending_config_changed"] is True


def test_on_boot_triggers_rollback_when_attempts_exceeded():
    fs = MockFileSystem()
    system = MockSystem()
    manager = BootManager(fs=fs, system=system, max_attempts=1)

    fs.write_bytes("app/main.py", b"broken")
    fs.write_bytes("app_prev/main.py", b"stable")
    fs.write_text("config.json", "current-config")
    fs.write_text("config_prev.json", "previous-config")
    fs.write_text(
        "boot_state.json",
        json.dumps(
            {
                "boot_count": 1,
                "boot_succeeded": False,
                "current_version": "2.0.0",
                "previous_version": "1.0.0",
                "config_version": "2.0.0",
                "previous_config_version": "1.0.0",
                "pending_app_changed": True,
                "pending_config_changed": True,
            }
        ),
    )

    manager.on_boot()

    assert fs.read_bytes("app/main.py") == b"stable"
    assert fs.read_text("config.json") == "previous-config"
    assert system.reset_calls == 1
    state = json.loads(fs.read_text("boot_state.json"))
    assert state["current_version"] == "1.0.0"
    assert state["config_version"] == "1.0.0"
    assert state["pending_app_changed"] is False
    assert state["pending_config_changed"] is False


def test_on_boot_restores_config_when_only_config_backup_exists():
    fs = MockFileSystem()
    system = MockSystem()
    manager = BootManager(fs=fs, system=system, max_attempts=1)

    fs.write_bytes("app/main.py", b"current-app")
    fs.write_text("config.json", "broken-config")
    fs.write_text("config_prev.json", "stable-config")
    fs.write_text(
        "boot_state.json",
        json.dumps(
            {
                "boot_count": 1,
                "boot_succeeded": False,
                "current_version": "2.0.0",
                "previous_version": "1.9.0",
                "config_version": "2.0.0",
                "previous_config_version": "1.9.0",
                "pending_app_changed": False,
                "pending_config_changed": True,
            }
        ),
    )

    manager.on_boot()

    assert fs.read_bytes("app/main.py") == b"current-app"
    assert fs.read_text("config.json") == "stable-config"
    assert system.reset_calls == 1
    state = json.loads(fs.read_text("boot_state.json"))
    assert state["current_version"] == "2.0.0"
    assert state["config_version"] == "1.9.0"


def test_on_boot_keeps_current_app_when_stale_app_backup_exists_for_config_only_failure():
    fs = MockFileSystem()
    system = MockSystem()
    manager = BootManager(fs=fs, system=system, max_attempts=1)

    fs.write_bytes("app/main.py", b"current-app")
    fs.write_bytes("app_prev/main.py", b"stale-old-app")
    fs.write_text("config.json", "broken-config")
    fs.write_text("config_prev.json", "stable-config")
    fs.write_text(
        "boot_state.json",
        json.dumps(
            {
                "boot_count": 1,
                "boot_succeeded": False,
                "current_version": "2.0.0",
                "previous_version": "1.9.0",
                "config_version": "2.0.0",
                "previous_config_version": "1.9.0",
                "pending_app_changed": False,
                "pending_config_changed": True,
            }
        ),
    )

    manager.on_boot()

    assert fs.read_bytes("app/main.py") == b"current-app"
    assert fs.read_text("config.json") == "stable-config"


def test_on_boot_restores_app_only_when_only_app_changed():
    fs = MockFileSystem()
    system = MockSystem()
    manager = BootManager(fs=fs, system=system, max_attempts=1)

    fs.write_bytes("app/main.py", b"broken-app")
    fs.write_bytes("app_prev/main.py", b"stable-app")
    fs.write_text("config.json", "current-config")
    fs.write_text("config_prev.json", "stale-config")
    fs.write_text(
        "boot_state.json",
        json.dumps(
            {
                "boot_count": 1,
                "boot_succeeded": False,
                "current_version": "2.0.0",
                "previous_version": "1.9.0",
                "config_version": "2.0.0",
                "previous_config_version": "1.9.0",
                "pending_app_changed": True,
                "pending_config_changed": False,
            }
        ),
    )

    manager.on_boot()

    assert fs.read_bytes("app/main.py") == b"stable-app"
    assert fs.read_text("config.json") == "current-config"
