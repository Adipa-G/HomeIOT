import sys
import types

import pytest

from edge.shared.hal.watchdog import MicroPythonWatchdog


class _FakeTime(types.ModuleType):
    def __init__(self):
        super().__init__("utime")
        self.now = 0

    def ticks_ms(self):
        return self.now

    @staticmethod
    def ticks_diff(a, b):
        return a - b


def _fake_machine(timer_error=None, wdt_error=None, timer_rejects_hard=False):
    machine = types.ModuleType("machine")
    machine.wdts = []
    machine.timers = []

    class WDT:
        def __init__(self, *args, **kwargs):
            if wdt_error is not None:
                raise wdt_error
            self.args = args
            self.kwargs = kwargs
            self.feed_calls = 0
            machine.wdts.append(self)

        def feed(self):
            self.feed_calls += 1

    class Timer:
        PERIODIC = 1

        def __init__(self, timer_id, mode, period, callback, **kwargs):
            if timer_error is not None:
                raise timer_error
            if timer_rejects_hard and "hard" in kwargs:
                raise TypeError("unexpected keyword argument 'hard'")
            self.timer_id = timer_id
            self.mode = mode
            self.period = period
            self.callback = callback
            self.kwargs = kwargs
            self.deinit_calls = 0
            machine.timers.append(self)

        def deinit(self):
            self.deinit_calls += 1

    machine.WDT = WDT
    machine.Timer = Timer
    return machine


def _watchdog_class(hardware_max_ms=None):
    # A fresh subclass per test keeps the class-level shared WDT state isolated.
    class _Watchdog(MicroPythonWatchdog):
        HARDWARE_MAX_TIMEOUT_MS = hardware_max_ms

    return _Watchdog


@pytest.fixture
def fake_time(monkeypatch):
    clock = _FakeTime()
    monkeypatch.setitem(sys.modules, "utime", clock)
    return clock


def _install_machine(monkeypatch, **kwargs):
    machine = _fake_machine(**kwargs)
    monkeypatch.setitem(sys.modules, "machine", machine)
    return machine


def test_init_passes_timeout_as_keyword_without_extension_timer(monkeypatch, fake_time):
    machine = _install_machine(monkeypatch)
    watchdog = _watchdog_class()()

    watchdog.init(120000)

    assert len(machine.wdts) == 1
    assert machine.wdts[0].args == ()
    assert machine.wdts[0].kwargs == {"timeout": 120000}
    assert machine.timers == []
    assert watchdog.get_feed_interval_ms() == 60000


def test_feed_interval_is_none_before_init():
    assert _watchdog_class()().get_feed_interval_ms() is None


def test_feed_is_noop_before_init():
    _watchdog_class()().feed()


def test_feed_feeds_hardware_wdt(monkeypatch, fake_time):
    machine = _install_machine(monkeypatch)
    watchdog = _watchdog_class()()
    watchdog.init(120000)

    watchdog.feed()

    assert machine.wdts[0].feed_calls == 1


def test_instances_share_one_hardware_wdt(monkeypatch, fake_time):
    machine = _install_machine(monkeypatch)
    watchdog_class = _watchdog_class()
    watchdog_class().init(120000)

    second = watchdog_class()
    second.init(120000)
    second.feed()

    assert len(machine.wdts) == 1
    assert machine.wdts[0].feed_calls == 1


def test_long_timeout_uses_hardware_limit_and_hard_extension_timer(monkeypatch, fake_time):
    machine = _install_machine(monkeypatch)
    watchdog = _watchdog_class(hardware_max_ms=8000)()

    watchdog.init(120000)

    assert machine.wdts[0].kwargs == {"timeout": 8000}
    assert len(machine.timers) == 1
    timer = machine.timers[0]
    assert timer.timer_id == -1
    assert timer.mode == machine.Timer.PERIODIC
    assert timer.period == 4000
    assert timer.kwargs == {"hard": True}
    assert watchdog.get_feed_interval_ms() == 4000


def test_timeout_within_hardware_limit_skips_extension_timer(monkeypatch, fake_time):
    machine = _install_machine(monkeypatch)
    watchdog = _watchdog_class(hardware_max_ms=8000)()

    watchdog.init(5000)

    assert machine.wdts[0].kwargs == {"timeout": 5000}
    assert machine.timers == []


def test_extension_timer_feeds_only_within_software_timeout(monkeypatch, fake_time):
    machine = _install_machine(monkeypatch)
    watchdog = _watchdog_class(hardware_max_ms=8000)()
    watchdog.init(120000)
    wdt = machine.wdts[0]
    timer = machine.timers[0]

    fake_time.now = 100000
    timer.callback(timer)
    assert wdt.feed_calls == 1

    # No application feed for the full software timeout: stop feeding the hardware.
    fake_time.now = 120000
    timer.callback(timer)
    assert wdt.feed_calls == 1

    watchdog.feed()
    assert wdt.feed_calls == 2

    fake_time.now = 230000
    timer.callback(timer)
    assert wdt.feed_calls == 3


def test_extension_timer_falls_back_when_hard_is_unsupported(monkeypatch, fake_time):
    machine = _install_machine(monkeypatch, timer_rejects_hard=True)
    watchdog = _watchdog_class(hardware_max_ms=8000)()

    watchdog.init(120000)

    assert machine.timers[0].kwargs == {}
    assert len(machine.wdts) == 1


def test_timer_failure_leaves_hardware_wdt_disabled(monkeypatch, fake_time):
    machine = _install_machine(monkeypatch, timer_error=RuntimeError("no timers"))
    watchdog_class = _watchdog_class(hardware_max_ms=8000)
    watchdog = watchdog_class()

    with pytest.raises(RuntimeError):
        watchdog.init(120000)

    assert machine.wdts == []
    assert watchdog_class._shared_wdt is None
    assert watchdog.get_feed_interval_ms() is None


def test_wdt_failure_stops_extension_timer(monkeypatch, fake_time):
    machine = _install_machine(monkeypatch, wdt_error=ValueError("timeout exceeds 8388"))
    watchdog_class = _watchdog_class(hardware_max_ms=8000)

    with pytest.raises(ValueError):
        watchdog_class().init(120000)

    assert machine.timers[0].deinit_calls == 1
    assert watchdog_class._shared_wdt is None
    assert watchdog_class._shared_timer is None
