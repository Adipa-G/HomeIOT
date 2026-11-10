import json

from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import CONFIG_PATH, LoggingConfig
from edge.shared.app.logger import EdgeLogger

WATCHDOG_TIMEOUT_MS = 120000


def load_max_attempts(fs, path=CONFIG_PATH, default_value=3):
    if not fs.exists(path):
        return default_value
    try:
        payload = json.loads(fs.read_text(path))
        return int(payload.get("max_boot_attempts", default_value))
    except Exception:
        return default_value


def run_boot(fs, system, watchdog) -> None:
    """boot.py path: arm the watchdog and let BootManager count attempts or roll back."""
    logger = EdgeLogger(system=system, logging_config=LoggingConfig(enabled_uplink=False))

    logger.info("Boot sequence started")
    try:
        watchdog.init(WATCHDOG_TIMEOUT_MS)
        logger.info("Watchdog initialized", {"timeout_ms": WATCHDOG_TIMEOUT_MS})
    except Exception as exc:
        logger.warn("Watchdog initialization skipped", {"error": str(exc)})
    max_attempts = load_max_attempts(fs)
    logger.info("Boot config loaded", {"max_boot_attempts": max_attempts})

    boot_manager = BootManager(fs=fs, system=system, max_attempts=max_attempts, logger=logger)
    logger.info("Running boot manager")
    boot_manager.on_boot()
