import json

from edge.shared.app import boot_sequence
from edge.shared.app.boot_sequence import WATCHDOG_TIMEOUT_MS, load_max_attempts, run_boot


class _FakeFs:
    def __init__(self, files=None):
        self.files = files or {}

    def exists(self, path):
        return path in self.files

    def read_text(self, path):
        return self.files[path]


class _FakeSystem:
    def time_ms(self):
        return 0


class _FakeWatchdog:
    def __init__(self, error=None):
        self.error = error
        self.init_calls = []

    def init(self, timeout_ms):
        self.init_calls.append(timeout_ms)
        if self.error is not None:
            raise self.error


class _RecordingBootManager:
    instances = []

    def __init__(self, fs, system, max_attempts, logger):
        self.fs = fs
        self.max_attempts = max_attempts
        self.on_boot_calls = 0
        _RecordingBootManager.instances.append(self)

    def on_boot(self):
        self.on_boot_calls += 1


def test_load_max_attempts_defaults_when_config_missing():
    assert load_max_attempts(_FakeFs()) == 3


def test_load_max_attempts_reads_config_value():
    fs = _FakeFs({"config.json": json.dumps({"max_boot_attempts": 5})})

    assert load_max_attempts(fs) == 5


def test_load_max_attempts_defaults_when_config_invalid():
    fs = _FakeFs({"config.json": "{not json"})

    assert load_max_attempts(fs, default_value=4) == 4


def test_run_boot_arms_watchdog_and_runs_boot_manager(monkeypatch):
    _RecordingBootManager.instances = []
    monkeypatch.setattr(boot_sequence, "BootManager", _RecordingBootManager)
    fs = _FakeFs({"config.json": json.dumps({"max_boot_attempts": 7})})
    watchdog = _FakeWatchdog()

    run_boot(fs=fs, system=_FakeSystem(), watchdog=watchdog)

    assert watchdog.init_calls == [WATCHDOG_TIMEOUT_MS]
    [manager] = _RecordingBootManager.instances
    assert manager.fs is fs
    assert manager.max_attempts == 7
    assert manager.on_boot_calls == 1


def test_run_boot_still_runs_boot_manager_when_watchdog_init_fails(monkeypatch):
    _RecordingBootManager.instances = []
    monkeypatch.setattr(boot_sequence, "BootManager", _RecordingBootManager)

    run_boot(fs=_FakeFs(), system=_FakeSystem(), watchdog=_FakeWatchdog(error=RuntimeError("no wdt")))

    [manager] = _RecordingBootManager.instances
    assert manager.max_attempts == 3
    assert manager.on_boot_calls == 1
