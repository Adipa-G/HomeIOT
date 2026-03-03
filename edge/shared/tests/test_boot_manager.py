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


def test_set_new_version_swaps_staging_and_backup():
    fs = MockFileSystem()
    system = MockSystem()
    manager = BootManager(fs=fs, system=system, max_attempts=3)

    manager.on_boot()
    fs.write_bytes("app/main.py", b"old")
    fs.write_bytes("app_staging/main.py", b"new")

    manager.set_new_version("1.2.0")

    assert fs.read_bytes("app/main.py") == b"new"
    assert fs.read_bytes("app_prev/main.py") == b"old"
    state = json.loads(fs.read_text("boot_state.json"))
    assert state["current_version"] == "1.2.0"


def test_on_boot_triggers_rollback_when_attempts_exceeded():
    fs = MockFileSystem()
    system = MockSystem()
    manager = BootManager(fs=fs, system=system, max_attempts=1)

    fs.write_bytes("app/main.py", b"broken")
    fs.write_bytes("app_prev/main.py", b"stable")
    fs.write_text(
        "boot_state.json",
        json.dumps(
            {
                "boot_count": 1,
                "boot_succeeded": False,
                "current_version": "2.0.0",
                "previous_version": "1.0.0",
            }
        ),
    )

    manager.on_boot()

    assert fs.read_bytes("app/main.py") == b"stable"
    assert system.reset_calls == 1
    state = json.loads(fs.read_text("boot_state.json"))
    assert state["current_version"] == "1.0.0"
