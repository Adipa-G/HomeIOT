import sys

# Both USB deploy and OTA place code under /app/edge/.
# Prepend /app so `import edge.…` resolves correctly.
if "app" not in sys.path:
    sys.path.insert(0, "app")

from edge.shared.app.boot_sequence import run_boot
from edge.platforms.esp32.hal.filesystem import MicroPythonFileSystem
from edge.platforms.esp32.hal.system import MicroPythonSystem
from edge.platforms.esp32.hal.watchdog import MicroPythonWatchdog


def main() -> None:
    print("[boot] boot.py start")
    run_boot(fs=MicroPythonFileSystem(), system=MicroPythonSystem(), watchdog=MicroPythonWatchdog())


main()
