import sys

import pytest

from edge.platforms.pico.hal.watchdog import PicoWatchdog
from edge.shared.tests.mocks.fake_module import fake_module


def test_pico_watchdog_stays_below_rp2040_hardware_limit() -> None:
    limit = PicoWatchdog.HARDWARE_MAX_TIMEOUT_MS
    assert limit is not None and limit <= 8388


def test_pico_watchdog_extends_long_timeout_with_timer(monkeypatch: pytest.MonkeyPatch) -> None:
    created: dict[str, object] = {}

    machine = fake_module("machine")

    class WDT:
        def __init__(self, **kwargs: object):
            created["wdt"] = kwargs

        def feed(self) -> None:
            pass

    class Timer:
        PERIODIC = 1

        def __init__(self, timer_id: int, mode: int, period: int, callback: object, **kwargs: object):
            created["timer_period"] = period

    machine.WDT = WDT
    machine.Timer = Timer

    def ticks_ms() -> int:
        return 0

    def ticks_diff(a: int, b: int) -> int:
        return a - b

    fake_time = fake_module("time")
    fake_time.ticks_ms = ticks_ms
    fake_time.ticks_diff = ticks_diff

    monkeypatch.setitem(sys.modules, "machine", machine)
    monkeypatch.setitem(sys.modules, "time", fake_time)

    # Subclass so the class-level shared WDT state does not leak into other tests.
    class _IsolatedPicoWatchdog(PicoWatchdog):
        pass

    watchdog = _IsolatedPicoWatchdog()
    watchdog.init(120000)

    assert created["wdt"] == {"timeout": 8000}
    assert created["timer_period"] == 4000
    assert watchdog.get_feed_interval_ms() == 4000
