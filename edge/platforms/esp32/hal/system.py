import binascii

from edge.shared.hal.interfaces import ISystem


class MicroPythonSystem(ISystem):
    def __init__(self):
        try:
            import utime as _time
        except ImportError:  # pragma: no cover - desktop fallback
            import time as _time
        self._time = _time

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

    def sleep_ms(self, milliseconds: int) -> None:
        if hasattr(self._time, "sleep_ms"):
            self._time.sleep_ms(milliseconds)
        else:
            self._time.sleep(milliseconds / 1000)
