from edge.shared.app.utc_time import MIN_SYNCED_YEAR, datetime_to_epoch, epoch_to_datetime, epoch_to_iso


class WallClock:
    """UTC time kept from the tick counter, anchored at each NTP sync.

    The RP2040 RTC stops during machine.lightsleep() and MicroPython resets the
    wall clock from it on wake, so time.gmtime() falls further behind with every
    sleep on a Pico W. The tick counter keeps running through light sleep on all
    supported ports, so anchor-plus-elapsed-ticks stays correct.
    """

    def __init__(self, system):
        self._system = system
        self._anchor_ms = None
        self._anchor_ticks = 0
        self._ntp_synced = False
        self.sync_failures = 0
        if self._system_clock_is_set():
            self._anchor_from_system()

    def is_synced(self):
        return self._anchor_ms is not None

    def is_ntp_synced(self):
        """True once NTP has succeeded since boot (not just a time taken from the RTC)."""
        return self._ntp_synced

    def sync(self):
        """Sync over NTP and re-anchor. Returns True on success."""
        try:
            synced = bool(self._system.sync_time())
        except Exception:
            synced = False
        if synced and self._anchor_from_system():
            self._ntp_synced = True
            self.sync_failures = 0
            return True
        self.sync_failures += 1
        return False

    def now_ms(self):
        """Unix milliseconds, or None before the first sync.

        Each call advances the anchor so tick-counter wraparound (about 12 days on
        MicroPython) is never reached as long as this runs at least every few days.
        """
        if self._anchor_ms is None:
            return None
        now = self._system.time_ms()
        self._anchor_ms += self._system.ticks_diff(now, self._anchor_ticks)
        self._anchor_ticks = now
        return self._anchor_ms

    def now_iso(self):
        now = self.now_ms()
        return None if now is None else epoch_to_iso(now // 1000)

    def iso_at_ticks(self, ticks):
        """UTC time of an earlier tick reading, or None before the first sync."""
        now = self.now_ms()
        if now is None:
            return None
        return epoch_to_iso((now - self._system.ticks_diff(self._anchor_ticks, ticks)) // 1000)

    def restore_system_clock(self):
        """Write the tick-derived time back to the hardware RTC so time.time() is right for modules."""
        now = self.now_ms()
        if now is None or not hasattr(self._system, "set_utc_datetime"):
            return False
        try:
            self._system.set_utc_datetime(epoch_to_datetime(now // 1000))
            return True
        except Exception:
            return False

    def _anchor_from_system(self):
        try:
            parts = self._system.utc_datetime()
        except Exception:
            return False
        if not parts or parts[0] < MIN_SYNCED_YEAR:
            return False
        self._anchor_ms = datetime_to_epoch(parts) * 1000
        self._anchor_ticks = self._system.time_ms()
        return True

    def _system_clock_is_set(self):
        if not hasattr(self._system, "clock_is_set"):
            return False
        try:
            return bool(self._system.clock_is_set())
        except Exception:
            return False
