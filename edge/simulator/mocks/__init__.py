"""Mock HAL implementations for PC simulator."""
from edge.simulator.mocks.mock_filesystem import SimulatorFileSystem
from edge.simulator.mocks.mock_http_client import SimulatorHttpClient
from edge.simulator.mocks.mock_network import SimulatorNetwork
from edge.simulator.mocks.mock_system import SimulatorSystem
from edge.simulator.mocks.mock_watchdog import SimulatorWatchdog

__all__ = [
    "SimulatorFileSystem",
    "SimulatorHttpClient",
    "SimulatorNetwork",
    "SimulatorSystem",
    "SimulatorWatchdog",
]
