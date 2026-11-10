import sys

# Both USB deploy and OTA place code under /app/edge/.
# Prepend /app so `import edge.…` resolves correctly.
if "app" not in sys.path:
    sys.path.insert(0, "app")

from edge.shared.app.boot_sequence import run_boot
from edge.platforms.pico.hal.filesystem import PicoFileSystem
from edge.platforms.pico.hal.system import PicoSystem
from edge.platforms.pico.hal.watchdog import PicoWatchdog


def main() -> None:
    print("[boot] boot.py start")
    run_boot(fs=PicoFileSystem(), system=PicoSystem(), watchdog=PicoWatchdog())


main()
