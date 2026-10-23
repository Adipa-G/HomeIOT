import sys
import types

from edge.shared.hal.system import MicroPythonSystem


def test_get_sleep_capabilities_detects_machine_sleep_functions(monkeypatch):
    machine = types.ModuleType("machine")
    machine.lightsleep = lambda *_args: None
    monkeypatch.setitem(sys.modules, "machine", machine)
    system = MicroPythonSystem()

    capabilities = system.get_sleep_capabilities()
    assert capabilities["lightsleep"] is True
    assert capabilities["deepsleep"] is False
    assert "runtime" in capabilities


def test_get_sleep_capabilities_returns_unsupported_on_desktop(monkeypatch):
    monkeypatch.delitem(sys.modules, "machine", raising=False)
    system = MicroPythonSystem()

    capabilities = system.get_sleep_capabilities()
    assert capabilities["lightsleep"] is False
    assert capabilities["deepsleep"] is False
    assert "runtime" in capabilities


def test_light_sleep_ms_uses_machine_lightsleep(monkeypatch):
    calls = []
    machine = types.ModuleType("machine")
    machine.lightsleep = lambda ms: calls.append(ms)
    monkeypatch.setitem(sys.modules, "machine", machine)
    system = MicroPythonSystem()

    assert system.light_sleep_ms(15000) is True
    assert calls == [15000]


def test_light_sleep_ms_falls_back_to_regular_sleep(monkeypatch):
    monkeypatch.setitem(sys.modules, "machine", types.ModuleType("machine"))
    system = MicroPythonSystem()
    sleeps = []
    monkeypatch.setattr(system, "sleep_ms", lambda ms: sleeps.append(ms))

    assert system.light_sleep_ms(20) is False
    assert sleeps == [20]


def test_reset_cause_maps_machine_constants(monkeypatch):
    machine = types.ModuleType("machine")
    machine.PWRON_RESET = 1
    machine.HARD_RESET = 2
    machine.WDT_RESET = 3
    machine.reset_cause = lambda: 3
    monkeypatch.setitem(sys.modules, "machine", machine)

    assert MicroPythonSystem().reset_cause() == "wdt_reset"


def test_reset_cause_reports_unmapped_value(monkeypatch):
    machine = types.ModuleType("machine")
    machine.PWRON_RESET = 1
    machine.reset_cause = lambda: 0
    monkeypatch.setitem(sys.modules, "machine", machine)

    assert MicroPythonSystem().reset_cause() == "unknown(0)"


def test_reset_cause_unknown_when_unavailable(monkeypatch):
    monkeypatch.setitem(sys.modules, "machine", types.ModuleType("machine"))

    assert MicroPythonSystem().reset_cause() == "unknown"
