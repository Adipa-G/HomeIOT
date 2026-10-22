from edge.shared.hal.interfaces import IWatchdog


class MicroPythonWatchdog(IWatchdog):
    # Largest timeout the hardware WDT accepts (None = no limit). Longer requested
    # timeouts are extended in software: a hard timer keeps feeding the hardware
    # WDT only while feed() keeps being called within the requested timeout.
    HARDWARE_MAX_TIMEOUT_MS = None

    _shared_wdt = None
    _shared_timer = None
    _shared_time = None
    _shared_timeout_ms = None
    _shared_hardware_timeout_ms = None
    _shared_last_feed_ms = 0

    def __init__(self):
        self._wdt = self.__class__._shared_wdt

    def init(self, timeout_ms: int) -> None:
        cls = self.__class__
        if cls._shared_wdt is None:
            try:
                import machine  # pyright: ignore[reportMissingImports]
                import utime as time_mod  # pyright: ignore[reportMissingImports]
            except ImportError as exc:  # pragma: no cover - desktop fallback
                raise RuntimeError("machine module is not available") from exc

            timeout_ms = int(timeout_ms)
            hardware_timeout_ms = timeout_ms
            if cls.HARDWARE_MAX_TIMEOUT_MS is not None:
                hardware_timeout_ms = min(timeout_ms, int(cls.HARDWARE_MAX_TIMEOUT_MS))

            cls._shared_time = time_mod
            cls._shared_last_feed_ms = time_mod.ticks_ms()

            # Create the extension timer before the WDT: a started WDT cannot be
            # stopped, so a timer failure must leave the device without a WDT
            # rather than resetting every few seconds.
            timer = None
            if hardware_timeout_ms < timeout_ms:
                timer = cls._create_extension_timer(machine, time_mod, timeout_ms, hardware_timeout_ms)
            try:
                # The first positional WDT argument is the id, so timeout must be a keyword.
                wdt = machine.WDT(timeout=hardware_timeout_ms)
            except Exception:
                if timer is not None:
                    timer.deinit()
                raise

            cls._shared_timer = timer
            cls._shared_timeout_ms = timeout_ms
            cls._shared_hardware_timeout_ms = hardware_timeout_ms
            cls._shared_wdt = wdt
        self._wdt = cls._shared_wdt

    def feed(self) -> None:
        cls = self.__class__
        target = self._wdt or cls._shared_wdt
        if target is not None:
            if cls._shared_time is not None:
                cls._shared_last_feed_ms = cls._shared_time.ticks_ms()
            target.feed()

    def get_feed_interval_ms(self):
        cls = self.__class__
        if cls._shared_wdt is None or cls._shared_hardware_timeout_ms is None:
            return None
        return max(1, cls._shared_hardware_timeout_ms // 2)

    @classmethod
    def _create_extension_timer(cls, machine, time_mod, timeout_ms, hardware_timeout_ms):
        ticks_ms = time_mod.ticks_ms
        ticks_diff = time_mod.ticks_diff

        # Runs in hard-IRQ context on rp2: must not allocate.
        def _on_timer(_timer):
            wdt = cls._shared_wdt
            if wdt is not None and ticks_diff(ticks_ms(), cls._shared_last_feed_ms) < timeout_ms:
                wdt.feed()

        period_ms = max(1, hardware_timeout_ms // 2)
        try:
            return machine.Timer(-1, mode=machine.Timer.PERIODIC, period=period_ms, callback=_on_timer, hard=True)
        except TypeError:
            return machine.Timer(-1, mode=machine.Timer.PERIODIC, period=period_ms, callback=_on_timer)
