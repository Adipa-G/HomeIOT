import sys

from edge.platforms.pico.hal.watchdog import PicoWatchdog
from edge.shared.tests.mocks.fake_module import fake_module


def test_pico_watchdog_stays_below_rp2040_hardware_limit():
    assert PicoWatchdog.HARDWARE_MAX_TIMEOUT_MS <= 8388


def test_pico_watchdog_extends_long_timeout_with_timer(monkeypatch):
    created = {}

    machine = fake_module("machine")

    class WDT:
        def __init__(self, **kwargs):
            created["wdt"] = kwargs

        def feed(self):
            pass

    class Timer:
        PERIODIC = 1

        def __init__(self, timer_id, mode, period, callback, **kwargs):
            created["timer_period"] = period

    machine.WDT = WDT
    machine.Timer = Timer

    fake_time = fake_module("time")
    fake_time.ticks_ms = lambda: 0
    fake_time.ticks_diff = lambda a, b: a - b

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
