import sys

# Both USB deploy and OTA place code under /app/edge/.
# Prepend /app so `import edge.…` resolves correctly.
if "app" not in sys.path:
    sys.path.insert(0, "app")

from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import Config
from edge.shared.app.control_loop import run_control_loop
from edge.shared.app.device_control import DeviceControlClient
from edge.shared.app.logger import EdgeLogger
from edge.shared.app.module_runtime import ModuleRuntime
from edge.shared.app.presence import PresenceService
from edge.shared.app.updater import Updater
from edge.platforms.esp32.hal.filesystem import MicroPythonFileSystem
from edge.platforms.esp32.hal.http_client import MicroPythonHttpClient
from edge.platforms.esp32.hal.network import MicroPythonNetwork
from edge.platforms.esp32.hal.system import MicroPythonSystem
from edge.platforms.esp32.hal.watchdog import MicroPythonWatchdog


def run_main() -> None:
    print("[main] main.py start")
    fs = MicroPythonFileSystem()
    system = MicroPythonSystem()
    http = MicroPythonHttpClient()
    network = MicroPythonNetwork()
    watchdog = MicroPythonWatchdog()

    config = Config.load(fs, system=system)
    logger = EdgeLogger(
        system=system,
        http=http,
        device_id=config.device_id,
        api_url=config.api_url,
        api_key=config.api_key,
        logging_config=config.logging,
    )

    logger.info("Main startup")
    logger.info("Configuration loaded", {"device_id": config.device_id})

    logger.info("Attempting WiFi connection", {"ssid": config.wifi_ssid})
    try:
        network.connect(config.wifi_ssid, config.wifi_password)
        logger.info("WiFi connected", {"ip": network.get_ip()})
        if system.sync_time():
            logger.info("NTP time synced")
        else:
            logger.warn("NTP time sync failed; timestamps may be inaccurate")
    except Exception as exc:
        logger.warn("WiFi connection failed; continuing in offline mode", {"error": str(exc)})

    boot_manager = BootManager(
        fs=fs,
        system=system,
        max_attempts=config.max_boot_attempts,
        logger=logger,
    )

    presence = PresenceService(http=http, network=network, system=system, config=config, logger=logger)
    updater = Updater(
        fs=fs,
        http=http,
        system=system,
        config=config,
        boot_manager=boot_manager,
        platform="esp32",
        logger=logger,
    )
    device_control = DeviceControlClient(http=http, config=config, fs=fs, logger=logger)
    module_runtime = ModuleRuntime(system=system, device_control=device_control, config=config, fs=fs, logger=logger)

    state = boot_manager.get_state()

    if state.get("current_version"):
        config.current_version = state["current_version"]

    if network.is_connected():
        logger.info("Registering device presence", {"version": config.current_version})
        try:
            presence.register(config.current_version)
        except Exception as exc:
            logger.warn("Device registration threw exception", {"error": str(exc)})

        logger.info("Checking for OTA updates")
        try:
            update_info = updater.check()
        except Exception as exc:
            logger.warn("OTA check threw exception", {"error": str(exc)})
            update_info = None
        if update_info is not None:
            logger.info("OTA update will be applied", {"version": update_info.version})
            try:
                updater.apply(update_info)
            except Exception as exc:
                logger.warn("OTA apply threw exception", {"error": str(exc)})
    else:
        logger.warn("Skipping registration and OTA check while offline")

    if network.is_connected():
        try:
            module_runtime.flush_pending_timeout_result()
        except Exception as exc:
            logger.warn("Timeout marker flush threw exception", {"error": str(exc)})

    if network.is_connected():
        try:
            module_runtime.flush_pending_module_status()
        except Exception as exc:
            logger.warn("Module-status marker flush threw exception", {"error": str(exc)})


    boot_manager.mark_success()
    logger.info("Boot path completed, entering control loop")
    logger.flush("startup")

    run_control_loop(
        system=system,
        presence=presence,
        device_control=device_control,
        module_runtime=module_runtime,
        logger=logger,
        config=config,
        network=network,
        watchdog=watchdog,
        updater=updater,
    )


run_main()
