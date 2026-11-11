"""Edge device PC simulator worker.

Runs the same control loop as a real ESP32/Pico device but on a PC using CPython.
Uses mock HAL implementations instead of hardware-specific modules.
"""

import argparse
import json
import logging
import signal
import sys
from pathlib import Path

# Ensure edge module can be imported
if "." not in sys.path:
    sys.path.insert(0, ".")

from edge.shared.app import startup
from edge.shared.app.config import Config
from edge.simulator.mocks import (
    SimulatorFileSystem,
    SimulatorHttpClient,
    SimulatorNetwork,
    SimulatorSystem,
    SimulatorWatchdog,
)


# Setup Python logging for simulator output
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s - %(message)s",
)
logger_py = logging.getLogger("simulator")

TEMPLATE_CONFIG_PATH = Path(__file__).resolve().parent / "config.template.json"


class SimulatorShutdown(Exception):
    """Raised when simulator receives shutdown signal."""

    pass


def _setup_signal_handlers():
    """Setup graceful shutdown on Ctrl+C."""

    def _signal_handler(signum, frame):
        logger_py.info("Shutdown signal received, stopping simulator...")
        raise SimulatorShutdown()

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)


def _require_requests():
    """Exit early: without `requests` every API call fails and the simulator only logs warnings."""
    try:
        import requests  # noqa: F401
    except ImportError:
        logger_py.error(
            "The simulator needs the 'requests' package, which is not installed for %s. "
            "Run `uv sync` from the repository root, then start the simulator with `uv run`.",
            sys.executable,
        )
        sys.exit(1)


def run_simulator(
    config_path: str,
    device_id: str | None = None,
    api_url: str | None = None,
    api_key: str | None = None,
    max_iterations: int | None = None,
):
    """Run the edge device simulator.

    Args:
        config_path: Path to config.json
        device_id: Override device ID from config
        api_url: Override API URL from config
        api_key: Override API key from config
        max_iterations: Limit control loop iterations (for testing)
    """
    logger_py.info("Starting edge device simulator")
    _require_requests()
    _setup_signal_handlers()

    try:
        # Initialize mock HAL
        fs = SimulatorFileSystem()
        system = SimulatorSystem(device_id=device_id)
        http = SimulatorHttpClient()
        network = SimulatorNetwork()
        watchdog = SimulatorWatchdog()

        # Load config
        config = Config.load(fs, system=system, path=config_path)
        
        # Override config if CLI args provided
        if device_id:
            config.device_id = device_id
        if api_url:
            config.api_url = api_url
        if api_key:
            config.api_key = api_key

        logger_py.info(
            f"Configuration loaded: device_id={config.device_id}, "
            f"api_url={config.api_url}"
        )

        # OTA stays off: applying a release would overwrite files in the
        # working directory (the repository) and then request a device reset.
        runtime = startup.create_runtime(
            fs=fs,
            system=system,
            http=http,
            network=network,
            watchdog=watchdog,
            config=config,
            platform="simulator",
            enable_ota=False,
        )
        startup.start(runtime)

        logger_py.info("=" * 70)
        logger_py.info(f"Simulator running. Device: {config.device_id}")
        logger_py.info(f"API: {config.api_url}")
        logger_py.info("View logs at: http://localhost:5173 (web dashboard)")
        logger_py.info("Press Ctrl+C to stop")
        logger_py.info("=" * 70)

        startup.run(runtime, max_iterations=max_iterations)

        logger_py.info("Control loop exited")

    except SimulatorShutdown:
        logger_py.info("Simulator stopped by user")
    except Exception as exc:
        logger_py.exception(f"Simulator error: {exc}")
        sys.exit(1)
    finally:
        logger_py.info("Simulator shutdown complete")


def _resolve_config_path(config_path: str) -> str:
    """Return config_path, or the bundled template (with a warning) when it doesn't exist."""
    if Path(config_path).exists():
        return config_path
    if not TEMPLATE_CONFIG_PATH.exists():
        logger_py.error(f"Config file not found: {config_path}")
        sys.exit(1)
    logger_py.warning(
        f"Config file not found: {config_path}; falling back to the template "
        f"{TEMPLATE_CONFIG_PATH}. Copy it and edit the copy to use your own settings."
    )
    return str(TEMPLATE_CONFIG_PATH)


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run an edge device simulator on your PC"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to config.json (default: config.json; falls back to edge/simulator/config.template.json if missing)",
    )
    parser.add_argument(
        "--device-id",
        type=str,
        help="Override device ID from config",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        help="Override API URL from config",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        help="Override API key from config",
    )
    parser.add_argument(
        "--max-iterations",
        type=int,
        help="Limit control loop iterations (for testing)",
    )

    args = parser.parse_args()

    run_simulator(
        config_path=_resolve_config_path(args.config),
        device_id=args.device_id,
        api_url=args.api_url,
        api_key=args.api_key,
        max_iterations=args.max_iterations,
    )


if __name__ == "__main__":
    main()
