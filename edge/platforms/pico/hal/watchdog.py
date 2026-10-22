from edge.shared.hal.watchdog import MicroPythonWatchdog


class PicoWatchdog(MicroPythonWatchdog):
    # RP2040 caps the hardware WDT at 8388 ms (RP2350: 16777 ms); stay below both.
    HARDWARE_MAX_TIMEOUT_MS = 8000


__all__ = ["PicoWatchdog"]
