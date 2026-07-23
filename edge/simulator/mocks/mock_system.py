"""Mock system HAL for PC simulator."""
import time
import uuid

from edge.shared.hal.interfaces import ISystem


class SimulatorSystem(ISystem):
    """CPython-compatible system implementation for PC simulator."""

    def __init__(self, device_id: str = None):
        self._unique_id = device_id or f"sim-{uuid.uuid4().hex[:8]}"
        self._boot_time_s = time.time()

    def reset(self) -> None:
        """Log reset instead of actually resetting."""
        raise RuntimeError(
            "Simulator received reset command. This would reset a real device."
        )

    def unique_id(self) -> str:
        """Return fixed device ID."""
        return self._unique_id

    def time_ms(self) -> int:
        """Return current time in milliseconds."""
        return int(time.time() * 1000)

    def ticks_diff(self, a: int, b: int) -> int:
        """Return a - b (wall-clock ms never wraps in the simulator)."""
        return a - b

    def ticks_add(self, ticks: int, delta: int) -> int:
        """Return ticks + delta."""
        return ticks + delta

    def uptime_ms(self) -> int:
        """Return uptime since boot in milliseconds."""
        elapsed_s = time.time() - self._boot_time_s
        return int(elapsed_s * 1000)

    def free_memory_bytes(self) -> int:
        """Return simulated free memory (always report plenty for testing)."""
        return 1024 * 1024  # 1 MB

    def sleep_ms(self, milliseconds: int) -> None:
        """Sleep for specified milliseconds."""
        time.sleep(milliseconds / 1000.0)

    def sync_time(self) -> bool:
        """Simulate time sync (always succeeds for simulator)."""
        return True
