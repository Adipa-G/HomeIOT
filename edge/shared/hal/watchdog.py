from edge.shared.hal.interfaces import IWatchdog


class MicroPythonWatchdog(IWatchdog):
    _shared_wdt = None

    def __init__(self):
        self._wdt = self.__class__._shared_wdt

    def init(self, timeout_ms: int) -> None:
        if self.__class__._shared_wdt is None:
            try:
                import machine  # pyright: ignore[reportMissingImports]
            except ImportError as exc:  # pragma: no cover - desktop fallback
                raise RuntimeError("machine module is not available") from exc
            self.__class__._shared_wdt = machine.WDT(timeout=timeout_ms)
        self._wdt = self.__class__._shared_wdt

    def feed(self) -> None:
        target = self._wdt or self.__class__._shared_wdt
        if target is not None:
            target.feed()
