"""Mock watchdog HAL for PC simulator."""
from edge.shared.hal.interfaces import IWatchdog


class SimulatorWatchdog(IWatchdog):
    """Mock watchdog implementation for PC simulator."""

    def __init__(self):
        self._timeout_ms = None
        self._feed_count = 0

    def init(self, timeout_ms: int) -> None:
        """Initialize watchdog with timeout (no-op for simulator)."""
        self._timeout_ms = timeout_ms

    def feed(self) -> None:
        """Feed watchdog (no-op for simulator)."""
        self._feed_count += 1
