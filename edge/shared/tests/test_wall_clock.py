from edge.shared.app.utc_time import epoch_to_datetime, iso_to_epoch
from edge.shared.app.wall_clock import WallClock


REAL_BOOT_S = iso_to_epoch("2026-10-22T00:00:00Z")


class _System:
    """Tick counter set by the test; the hardware clock reads 2021 until NTP and can be frozen."""

    def __init__(self, clock_set=False, sync_ok=True):
        self.ticks = 0
        self.clock_set = clock_set
        self.sync_ok = sync_ok
        self.frozen_rtc_s = None
        self.rtc_writes = []

    def time_ms(self):
        return self.ticks

    def ticks_diff(self, a, b):
        return a - b

    def clock_is_set(self):
        return self.clock_set

    def sync_time(self):
        if self.sync_ok:
            self.clock_set = True
            self.frozen_rtc_s = None
        return self.sync_ok

    def utc_datetime(self):
        if not self.clock_set:
            return (2021, 1, 1, 0, 0, 0)
        seconds = self.frozen_rtc_s if self.frozen_rtc_s is not None else REAL_BOOT_S + self.ticks // 1000
        return epoch_to_datetime(seconds)[:6]

    def set_utc_datetime(self, parts):
        self.rtc_writes.append(parts)


def test_unsynced_clock_reports_none():
    clock = WallClock(_System(clock_set=False))

    assert clock.is_synced() is False
    assert clock.now_ms() is None
    assert clock.now_iso() is None
    assert clock.iso_at_ticks(0) is None
    assert clock.restore_system_clock() is False


def test_anchors_from_hardware_clock_when_already_set():
    system = _System(clock_set=True)
    system.ticks = 5000

    clock = WallClock(system)

    assert clock.is_synced() is True
    assert clock.now_iso() == "2026-10-22T00:00:05Z"


def test_time_advances_with_ticks_even_when_hardware_clock_freezes():
    system = _System(clock_set=False)
    clock = WallClock(system)
    assert clock.sync() is True

    # The RP2040 RTC stops during light sleep; ticks keep counting.
    system.frozen_rtc_s = REAL_BOOT_S
    system.ticks = 3 * 3600 * 1000

    assert clock.now_iso() == "2026-10-22T03:00:00Z"


def test_iso_at_ticks_returns_time_of_earlier_reading():
    system = _System(clock_set=True)
    clock = WallClock(system)
    system.ticks = 600000

    assert clock.iso_at_ticks(60000) == "2026-10-22T00:01:00Z"


def test_failed_sync_keeps_unsynced():
    clock = WallClock(_System(clock_set=False, sync_ok=False))

    assert clock.sync() is False
    assert clock.is_synced() is False


def test_restore_system_clock_writes_tick_time():
    system = _System(clock_set=True)
    clock = WallClock(system)
    system.ticks = 90000

    assert clock.restore_system_clock() is True
    assert system.rtc_writes == [epoch_to_datetime(REAL_BOOT_S + 90)]


def test_anchor_advances_on_every_read():
    system = _System(clock_set=True)
    clock = WallClock(system)
    for minute in range(1, 6):
        system.ticks = minute * 60000
        clock.now_ms()

    assert clock.now_iso() == "2026-10-22T00:05:00Z"


def test_rtc_anchor_is_not_ntp_synced():
    clock = WallClock(_System(clock_set=True))

    assert clock.is_synced() is True
    assert clock.is_ntp_synced() is False


def test_sync_marks_ntp_synced_and_counts_failures():
    system = _System(clock_set=False, sync_ok=False)
    clock = WallClock(system)

    clock.sync()
    clock.sync()
    assert clock.sync_failures == 2
    assert clock.is_ntp_synced() is False

    system.sync_ok = True
    assert clock.sync() is True
    assert clock.is_ntp_synced() is True
    assert clock.sync_failures == 0
