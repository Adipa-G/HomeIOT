import sys

# Both USB deploy and OTA place code under /app/edge/.
# Prepend /app so `import edge.…` resolves correctly.
if "app" not in sys.path:
    sys.path.insert(0, "app")

import json

from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import CONFIG_PATH, LoggingConfig
from edge.shared.app.logger import EdgeLogger
from edge.platforms.pico.hal.filesystem import PicoFileSystem
from edge.platforms.pico.hal.system import PicoSystem
from edge.platforms.pico.hal.watchdog import PicoWatchdog


def _load_max_attempts(fs, path=CONFIG_PATH, default_value=3):
    if not fs.exists(path):
        return default_value
    try:
        payload = json.loads(fs.read_text(path))
        return int(payload.get("max_boot_attempts", default_value))
    except Exception:
        return default_value


def run_boot() -> None:
    print("[boot] boot.py start")
    fs = PicoFileSystem()
    system = PicoSystem()
    watchdog = PicoWatchdog()
    logger = EdgeLogger(system=system, logging_config=LoggingConfig(enabled_uplink=False))

    logger.info("Boot sequence started")
    try:
        watchdog.init(120000)
        logger.info("Watchdog initialized", {"timeout_ms": 120000})
    except Exception as exc:
        logger.warn("Watchdog initialization skipped", {"error": str(exc)})
    max_attempts = _load_max_attempts(fs)
    logger.info("Boot config loaded", {"max_boot_attempts": max_attempts})

    boot_manager = BootManager(fs=fs, system=system, max_attempts=max_attempts, logger=logger)
    logger.info("Running boot manager")
    boot_manager.on_boot()


run_boot()
