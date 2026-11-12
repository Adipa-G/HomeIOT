import importlib
import sys

import pytest

from edge.platforms.pico.hal.filesystem import PicoFileSystem
from edge.platforms.pico.hal.http_client import PicoHttpClient
from edge.platforms.pico.hal.network import PicoNetwork
from edge.platforms.pico.hal.system import PicoSystem
from edge.platforms.pico.hal.watchdog import PicoWatchdog
from edge.shared.app import boot_sequence, startup


def _import_entry_point(monkeypatch: pytest.MonkeyPatch, module_name: str) -> None:
    # Entry points run on import and prepend "app" to sys.path.
    monkeypatch.setattr(sys, "path", list(sys.path))
    monkeypatch.delitem(sys.modules, module_name, raising=False)
    importlib.import_module(module_name)
    sys.modules.pop(module_name, None)


def test_main_runs_shared_device_startup_with_pico_hal(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def record(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(startup, "run_device", record)

    _import_entry_point(monkeypatch, "edge.platforms.pico.src.main")

    [kwargs] = calls
    assert kwargs["platform"] == "pico"
    assert isinstance(kwargs["fs"], PicoFileSystem)
    assert isinstance(kwargs["system"], PicoSystem)
    assert isinstance(kwargs["http"], PicoHttpClient)
    assert isinstance(kwargs["network"], PicoNetwork)
    assert isinstance(kwargs["watchdog"], PicoWatchdog)


def test_boot_runs_shared_boot_sequence_with_pico_hal(monkeypatch: pytest.MonkeyPatch) -> None:
    calls: list[dict[str, object]] = []

    def record(**kwargs: object) -> None:
        calls.append(kwargs)

    monkeypatch.setattr(boot_sequence, "run_boot", record)

    _import_entry_point(monkeypatch, "edge.platforms.pico.src.boot")

    [kwargs] = calls
    assert isinstance(kwargs["fs"], PicoFileSystem)
    assert isinstance(kwargs["system"], PicoSystem)
    assert isinstance(kwargs["watchdog"], PicoWatchdog)
