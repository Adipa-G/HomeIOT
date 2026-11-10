import sys

# Both USB deploy and OTA place code under /app/edge/.
# Prepend /app so `import edge.…` resolves correctly.
if "app" not in sys.path:
    sys.path.insert(0, "app")

from edge.shared.app.startup import run_device
from edge.platforms.pico.hal.filesystem import PicoFileSystem
from edge.platforms.pico.hal.http_client import PicoHttpClient
from edge.platforms.pico.hal.network import PicoNetwork
from edge.platforms.pico.hal.system import PicoSystem
from edge.platforms.pico.hal.watchdog import PicoWatchdog


def run_main() -> None:
    print("[main] main.py start")
    run_device(
        fs=PicoFileSystem(),
        system=PicoSystem(),
        http=PicoHttpClient(),
        network=PicoNetwork(),
        watchdog=PicoWatchdog(),
        platform="pico",
    )


run_main()
