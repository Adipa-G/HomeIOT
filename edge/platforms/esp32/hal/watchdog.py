from edge.shared.hal.interfaces import IWatchdog


class MicroPythonWatchdog(IWatchdog):
    def __init__(self):
        self._wdt = None

    def init(self, timeout_ms: int) -> None:
        try:
            import machine
        except ImportError as exc:  # pragma: no cover - desktop fallback
            raise RuntimeError("machine module is not available") from exc
        self._wdt = machine.WDT(timeout=timeout_ms)

    def feed(self) -> None:
        if self._wdt is not None:
            self._wdt.feed()
