import pytest
import sys
import types

from edge.shared.hal.system import MicroPythonSystem
from edge.shared.tests.mocks.fake_module import fake_module


def test_get_sleep_capabilities_detects_machine_sleep_functions(monkeypatch: pytest.MonkeyPatch):
    def lightsleep(*_args: object) -> None:
        pass

    machine = fake_module("machine")
    machine.lightsleep = lightsleep
    monkeypatch.setitem(sys.modules, "machine", machine)
    system = MicroPythonSystem()

    capabilities = system.get_sleep_capabilities()
    assert capabilities["lightsleep"] is True
    assert capabilities["deepsleep"] is False
    assert "runtime" in capabilities


def test_get_sleep_capabilities_returns_unsupported_on_desktop(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delitem(sys.modules, "machine", raising=False)
    system = MicroPythonSystem()

    capabilities = system.get_sleep_capabilities()
    assert capabilities["lightsleep"] is False
    assert capabilities["deepsleep"] is False
    assert "runtime" in capabilities


def test_light_sleep_ms_uses_machine_lightsleep(monkeypatch: pytest.MonkeyPatch):
    calls: list[int] = []

    def lightsleep(ms: int) -> None:
        calls.append(ms)

    machine = fake_module("machine")
    machine.lightsleep = lightsleep
    monkeypatch.setitem(sys.modules, "machine", machine)
    system = MicroPythonSystem()

    assert system.light_sleep_ms(15000) is True
    assert calls == [15000]


def test_light_sleep_ms_falls_back_to_regular_sleep(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(sys.modules, "machine", fake_module("machine"))
    system = MicroPythonSystem()
    sleeps: list[int] = []

    def sleep_ms(ms: int) -> None:
        sleeps.append(ms)

    monkeypatch.setattr(system, "sleep_ms", sleep_ms)

    assert system.light_sleep_ms(20) is False
    assert sleeps == [20]


def test_reset_cause_maps_machine_constants(monkeypatch: pytest.MonkeyPatch):
    machine = fake_module("machine")
    machine.PWRON_RESET = 1
    machine.HARD_RESET = 2
    machine.WDT_RESET = 3
    machine.reset_cause = lambda: 3
    monkeypatch.setitem(sys.modules, "machine", machine)

    assert MicroPythonSystem().reset_cause() == "wdt_reset"


def test_reset_cause_reports_unmapped_value(monkeypatch: pytest.MonkeyPatch):
    machine = fake_module("machine")
    machine.PWRON_RESET = 1
    machine.reset_cause = lambda: 0
    monkeypatch.setitem(sys.modules, "machine", machine)

    assert MicroPythonSystem().reset_cause() == "unknown(0)"


def test_reset_cause_unknown_when_unavailable(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setitem(sys.modules, "machine", fake_module("machine"))

    assert MicroPythonSystem().reset_cause() == "unknown"


def _system_with_year(monkeypatch: pytest.MonkeyPatch, year: int) -> MicroPythonSystem:
    system = MicroPythonSystem()
    fake_time = types.SimpleNamespace(gmtime=lambda: (year, 1, 1, 0, 0, 0, 0, 1))
    monkeypatch.setattr(system, "_time", fake_time)
    return system


def test_clock_is_set_false_for_default_rp2_date(monkeypatch: pytest.MonkeyPatch):
    assert _system_with_year(monkeypatch, 2021).clock_is_set() is False


def test_clock_is_set_true_after_sync(monkeypatch: pytest.MonkeyPatch):
    assert _system_with_year(monkeypatch, 2026).clock_is_set() is True


def test_clock_is_set_true_when_gmtime_unavailable(monkeypatch: pytest.MonkeyPatch):
    system = MicroPythonSystem()
    monkeypatch.setattr(system, "_time", types.SimpleNamespace())
    assert system.clock_is_set() is True


def test_utc_datetime_reads_gmtime(monkeypatch: pytest.MonkeyPatch):
    system = MicroPythonSystem()
    monkeypatch.setattr(system, "_time", types.SimpleNamespace(gmtime=lambda: (2026, 10, 24, 9, 30, 15, 5, 297)))
    assert system.utc_datetime() == (2026, 10, 24, 9, 30, 15)


def test_set_utc_datetime_writes_rtc_in_machine_order(monkeypatch: pytest.MonkeyPatch):
    writes: list[tuple[int, ...]] = []

    class _Rtc:
        def datetime(self, value: tuple[int, ...]) -> None:
            writes.append(value)

    machine = fake_module("machine")
    machine.RTC = _Rtc
    monkeypatch.setitem(sys.modules, "machine", machine)

    MicroPythonSystem().set_utc_datetime((2026, 10, 24, 9, 30, 15, 5))

    assert writes == [(2026, 10, 24, 5, 9, 30, 15, 0)]
