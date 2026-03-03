from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import Config
from edge.shared.app.presence import PresenceService
from edge.shared.app.updater import Updater
from edge.platforms.esp32.hal.filesystem import MicroPythonFileSystem
from edge.platforms.esp32.hal.http_client import MicroPythonHttpClient
from edge.platforms.esp32.hal.network import MicroPythonNetwork
from edge.platforms.esp32.hal.system import MicroPythonSystem


def run_main() -> None:
    fs = MicroPythonFileSystem()
    system = MicroPythonSystem()
    http = MicroPythonHttpClient()
    network = MicroPythonNetwork()

    config = Config.load(fs)
    network.connect(config.wifi_ssid, config.wifi_password)

    boot_manager = BootManager(
        fs=fs,
        system=system,
        max_attempts=config.max_boot_attempts,
    )

    presence = PresenceService(http=http, network=network, system=system, config=config)
    updater = Updater(
        fs=fs,
        http=http,
        system=system,
        config=config,
        boot_manager=boot_manager,
    )

    state = boot_manager.get_state()

    if state.get("current_version"):
        config.current_version = state["current_version"]

    presence.register(config.current_version)

    update_info = updater.check()
    if update_info is not None:
        updater.apply(update_info)

    boot_manager.mark_success()
    presence.run_heartbeat_loop(interval_ms=config.heartbeat_interval_ms)


run_main()
