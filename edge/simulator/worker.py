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

from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import Config
from edge.shared.app.control_loop import run_control_loop
from edge.shared.app.device_control import DeviceControlClient
from edge.shared.app.logger import EdgeLogger
from edge.shared.app.module_runtime import ModuleRuntime
from edge.shared.app.presence import PresenceService
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


def run_simulator(
    config_path: str,
    device_id: str = None,
    api_url: str = None,
    api_key: str = None,
    max_iterations: int = None,
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

        # Initialize logger
        logger = EdgeLogger(
            system=system,
            http=http,
            device_id=config.device_id,
            api_url=config.api_url,
            api_key=config.api_key,
            logging_config=config.logging,
        )

        logger.info("Simulator startup")
        logger.info("Configuration loaded", {"device_id": config.device_id})

        # Network connection (simulator is always "connected")
        logger.info("Network ready (simulator mode - no WiFi needed)")
        if system.sync_time():
            logger.info("Time synced")
        else:
            logger.warn("Time sync failed")

        # Boot manager
        boot_manager = BootManager(
            fs=fs,
            system=system,
            max_attempts=config.max_boot_attempts,
            logger=logger,
        )

        # Initialize services
        presence = PresenceService(
            http=http, network=network, system=system, config=config, logger=logger
        )
        device_control = DeviceControlClient(
            http=http, config=config, fs=fs, logger=logger
        )
        module_runtime = ModuleRuntime(
            system=system,
            device_control=device_control,
            config=config,
            fs=fs,
            logger=logger,
        )

        # Get boot state
        state = boot_manager.get_state()
        if state.get("current_version"):
            config.current_version = state["current_version"]

        # Register device
        logger.info(
            "Registering device presence",
            {"version": config.current_version},
        )
        try:
            presence.register(config.current_version)
            logger_py.info("✓ Device registration successful")
        except Exception as exc:
            logger.warn("Device registration threw exception", {"error": str(exc)})
            logger_py.warning(f"✗ Device registration failed: {exc}")

        # Flush any pending state
        try:
            module_runtime.flush_pending_timeout_result()
        except Exception as exc:
            logger.warn("Timeout marker flush threw exception", {"error": str(exc)})

        try:
            module_runtime.flush_pending_module_status()
        except Exception as exc:
            logger.warn("Module-status marker flush threw exception", {"error": str(exc)})

        # Mark boot successful
        boot_manager.mark_success()
        logger.info("Boot path completed, entering control loop")
        logger.flush("startup")

        logger_py.info("=" * 70)
        logger_py.info(f"Simulator running. Device: {config.device_id}")
        logger_py.info(f"API: {config.api_url}")
        logger_py.info("View logs at: http://localhost:5173 (web dashboard)")
        logger_py.info("Press Ctrl+C to stop")
        logger_py.info("=" * 70)

        # Run control loop
        run_control_loop(
            system=system,
            presence=presence,
            device_control=device_control,
            module_runtime=module_runtime,
            logger=logger,
            config=config,
            network=network,
            watchdog=watchdog,
            max_iterations=max_iterations,
        )

        logger_py.info("Control loop exited")

    except SimulatorShutdown:
        logger_py.info("Simulator stopped by user")
    except Exception as exc:
        logger_py.exception(f"Simulator error: {exc}")
        sys.exit(1)
    finally:
        logger_py.info("Simulator shutdown complete")


def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(
        description="Run an edge device simulator on your PC"
    )
    parser.add_argument(
        "--config",
        type=str,
        default="config.json",
        help="Path to config.json (default: config.json)",
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

    # Verify config file exists
    if not Path(args.config).exists():
        logger_py.error(f"Config file not found: {args.config}")
        sys.exit(1)

    run_simulator(
        config_path=args.config,
        device_id=args.device_id,
        api_url=args.api_url,
        api_key=args.api_key,
        max_iterations=args.max_iterations,
    )


if __name__ == "__main__":
    main()
