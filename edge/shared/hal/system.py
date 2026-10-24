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

    def light_sleep_ms(self, milliseconds: int) -> bool:
        lightsleep = None
        try:
            import machine
            lightsleep = getattr(machine, "lightsleep", None)
        except ImportError:  # pragma: no cover - desktop fallback
            pass

        milliseconds = int(milliseconds)
        if callable(lightsleep) and milliseconds > 0:
            lightsleep(milliseconds)
            return True
        self.sleep_ms(milliseconds)
        return False

    _RESET_CAUSE_NAMES = (
        "PWRON_RESET",
        "HARD_RESET",
        "WDT_RESET",
        "DEEPSLEEP_RESET",
        "SOFT_RESET",
        "LOCKUP_RESET",
    )

    def reset_cause(self) -> str:
        try:
            import machine
        except ImportError:  # pragma: no cover - desktop fallback
            return "unknown"
        try:
            cause = machine.reset_cause()
        except Exception:
            return "unknown"
        for name in self._RESET_CAUSE_NAMES:
            if getattr(machine, name, None) == cause:
                return name.lower()
        return "unknown(" + str(cause) + ")"

    def get_sleep_capabilities(self) -> dict:
        capabilities = {"lightsleep": False, "deepsleep": False}
        try:
            import machine
            capabilities["lightsleep"] = callable(getattr(machine, "lightsleep", None))
            capabilities["deepsleep"] = callable(getattr(machine, "deepsleep", None))
        except ImportError:  # pragma: no cover - desktop fallback
            pass

        try:
            import sys
            implementation = sys.implementation
            capabilities["runtime"] = str(getattr(implementation, "name", "unknown"))
            version = getattr(implementation, "version", None)
            if version:
                capabilities["runtime_version"] = ".".join(str(part) for part in version[:3])
        except Exception:
            pass

        try:
            import os
            platform = os.uname()
            capabilities["platform"] = str(platform.sysname)
            capabilities["platform_release"] = str(platform.release)
            capabilities["machine"] = str(platform.machine)
        except (AttributeError, OSError):
            pass

        return capabilities

    def sync_time(self) -> bool:
        try:
            import ntptime
            ntptime.settime()
            return True
        except Exception:  # pragma: no cover - desktop fallback
            return False

    # Boards without a battery-backed RTC start at a fixed past date (rp2: 2021-01-01).
    _MIN_SYNCED_YEAR = 2024

    def clock_is_set(self) -> bool:
        gmtime = getattr(self._time, "gmtime", None)
        if not callable(gmtime):
            return True
        try:
            return gmtime()[0] >= self._MIN_SYNCED_YEAR
        except Exception:
            return True

    def utc_datetime(self) -> tuple:
        return tuple(self._time.gmtime()[:6])

    def set_utc_datetime(self, parts) -> None:
        import machine
        year, month, day, hour, minute, second, weekday = parts
        machine.RTC().datetime((year, month, day, weekday, hour, minute, second, 0))
