"""Mock network HAL for PC simulator."""
from edge.shared.hal.interfaces import INetwork


class SimulatorNetwork(INetwork):
    """Mock network implementation for PC simulator."""

    def __init__(self):
        self._connected = True
        self._ip = "127.0.0.1"

    def connect(self, ssid: str, password: str, timeout_ms: int = 15000) -> None:
        """Simulate successful WiFi connection."""
        self._connected = True

    def is_connected(self) -> bool:
        """Return connection status (always True for simulator)."""
        return self._connected

    def get_ip(self) -> str:
        """Return simulated IP address."""
        return self._ip

    def get_power_save_modes(self) -> dict:
        """Return no hardware power modes for the simulator."""
        return {}

    def set_power_save(self, mode: str) -> bool:
        """No-op for simulator."""
        return True

    def interface_active(self, enable: bool) -> None:
        """No-op for simulator."""
        pass

    def suspend(self) -> None:
        """Simulate powering the radio down; connect() restores it."""
        self._connected = False
