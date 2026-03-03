import json

from edge.shared.app.boot_manager import BootManager
from edge.platforms.esp32.hal.filesystem import MicroPythonFileSystem
from edge.platforms.esp32.hal.system import MicroPythonSystem
from edge.platforms.esp32.hal.watchdog import MicroPythonWatchdog


def _load_max_attempts(fs, path="config.json", default_value=3):
    if not fs.exists(path):
        return default_value
    try:
        payload = json.loads(fs.read_text(path))
        return int(payload.get("max_boot_attempts", default_value))
    except Exception:
        return default_value


def run_boot() -> None:
    fs = MicroPythonFileSystem()
    system = MicroPythonSystem()
    watchdog = MicroPythonWatchdog()

    watchdog.init(timeout_ms=30000)
    max_attempts = _load_max_attempts(fs)

    boot_manager = BootManager(fs=fs, system=system, max_attempts=max_attempts)
    boot_manager.on_boot()


run_boot()
