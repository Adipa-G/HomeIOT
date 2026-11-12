import importlib
import sys

import pytest

from edge.platforms.esp32.hal.filesystem import MicroPythonFileSystem
from edge.platforms.esp32.hal.http_client import MicroPythonHttpClient
from edge.platforms.esp32.hal.network import MicroPythonNetwork
from edge.platforms.esp32.hal.system import MicroPythonSystem
from edge.platforms.esp32.hal.watchdog import MicroPythonWatchdog
from edge.shared.app import boot_sequence, startup


def _import_entry_point(monkeypatch: pytest.MonkeyPatch, module_name: str) -> None:
    # Entry points run on import and prepend "app" to sys.path.
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.delitem(sys.modules, module_name, raising=False)
    importlib.import_module(module_name)
    sys.modules.pop(module_name, None)


def test_main_runs_shared_device_startup_with_esp32_hal(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def record(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(startup, "run_device", record)

    _import_entry_point(monkeypatch, "edge.platforms.esp32.src.main")

    [kwargs] = calls
    assert kwargs["platform"] == "esp32"
    assert isinstance(kwargs["fs"], MicroPythonFileSystem)
    assert isinstance(kwargs["system"], MicroPythonSystem)
    assert isinstance(kwargs["http"], MicroPythonHttpClient)
    assert isinstance(kwargs["network"], MicroPythonNetwork)
    assert isinstance(kwargs["watchdog"], MicroPythonWatchdog)


def test_boot_runs_shared_boot_sequence_with_esp32_hal(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def record(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(boot_sequence, "run_boot", record)

    _import_entry_point(monkeypatch, "edge.platforms.esp32.src.boot")

    [kwargs] = calls
    assert isinstance(kwargs["fs"], MicroPythonFileSystem)
    assert isinstance(kwargs["system"], MicroPythonSystem)
    assert isinstance(kwargs["watchdog"], MicroPythonWatchdog)
