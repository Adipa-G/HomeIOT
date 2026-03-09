from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import Config
from edge.shared.app.logger import EdgeLogger
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
    except Exception as exc:
        logger.error("WiFi connection failed", {"error": str(exc)})
        raise

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
        logger=logger,
    )

    state = boot_manager.get_state()

    if state.get("current_version"):
        config.current_version = state["current_version"]

    logger.info("Registering device presence", {"version": config.current_version})
    presence.register(config.current_version)

    logger.info("Checking for OTA updates")
    update_info = updater.check()
    if update_info is not None:
        logger.info("OTA update will be applied", {"version": update_info.version})
        updater.apply(update_info)

    boot_manager.mark_success()
    logger.info("Boot path completed, entering heartbeat loop")
    logger.flush("startup")
    presence.run_heartbeat_loop(interval_ms=config.heartbeat_interval_ms)


run_main()
