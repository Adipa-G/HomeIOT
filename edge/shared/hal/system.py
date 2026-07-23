import binascii

from edge.shared.hal.interfaces import ISystem


class MicroPythonSystem(ISystem):
    def __init__(self):
        try:
            import utime as _time
        except ImportError:  # pragma: no cover - desktop fallback
            import time as _time
        self._time = _time
        self._boot_ms = self.time_ms()

    def reset(self) -> None:
        try:
            import machine
        except ImportError as exc:  # pragma: no cover - desktop fallback
            raise RuntimeError("machine module is not available") from exc
        machine.reset()

    def unique_id(self) -> str:
        try:
            import machine
        except ImportError:  # pragma: no cover - desktop fallback
            return "desktop-test-device"
        return binascii.hexlify(machine.unique_id()).decode("ascii")

    def time_ms(self) -> int:
        if hasattr(self._time, "ticks_ms"):
            return self._time.ticks_ms()
        return int(self._time.time() * 1000)

    def ticks_diff(self, a: int, b: int) -> int:
        if hasattr(self._time, "ticks_diff"):
            return self._time.ticks_diff(a, b)
        return a - b

    def ticks_add(self, ticks: int, delta: int) -> int:
        if hasattr(self._time, "ticks_add"):
            return self._time.ticks_add(ticks, delta)
        return ticks + delta

    def uptime_ms(self) -> int:
        now = self.time_ms()
        if hasattr(self._time, "ticks_diff"):
            return self._time.ticks_diff(now, self._boot_ms)
        return now - self._boot_ms

    def free_memory_bytes(self) -> int:
        try:
            import gc
            gc.collect()
            return gc.mem_free()
        except (ImportError, AttributeError):  # pragma: no cover - desktop fallback
            return 0

    def sleep_ms(self, milliseconds: int) -> None:
        if hasattr(self._time, "sleep_ms"):
            self._time.sleep_ms(milliseconds)
        else:
            self._time.sleep(milliseconds / 1000)

    def sync_time(self) -> bool:
        try:
            import ntptime
            ntptime.settime()
            return True
        except Exception:  # pragma: no cover - desktop fallback
            return False
