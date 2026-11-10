import sys

# Both USB deploy and OTA place code under /app/edge/.
# Prepend /app so `import edge.…` resolves correctly.
if "app" not in sys.path:
    sys.path.insert(0, "app")

from edge.shared.app.startup import run_device
from edge.platforms.esp32.hal.filesystem import MicroPythonFileSystem
from edge.platforms.esp32.hal.http_client import MicroPythonHttpClient
from edge.platforms.esp32.hal.network import MicroPythonNetwork
from edge.platforms.esp32.hal.system import MicroPythonSystem
from edge.platforms.esp32.hal.watchdog import MicroPythonWatchdog


def run_main() -> None:
    print("[main] main.py start")
    run_device(
        fs=MicroPythonFileSystem(),
        system=MicroPythonSystem(),
        http=MicroPythonHttpClient(),
        network=MicroPythonNetwork(),
        watchdog=MicroPythonWatchdog(),
        platform="esp32",
    )


run_main()
