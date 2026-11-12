from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import CONFIG_PATH, Config
from edge.shared.app.control_loop import run_control_loop
from edge.shared.app.device_control import DeviceControlClient
from edge.shared.app.logger import EdgeLogger
from edge.shared.app.module_runtime import ModuleRuntime
from edge.shared.app.presence import PresenceService
from edge.shared.app.updater import Updater
from edge.shared.app.wall_clock import WallClock
from edge.shared.hal.interfaces import IFileSystem, IHttpClient, INetwork, ISystem, IWatchdog


class DeviceRuntime:
    """The HAL, configuration and services shared by device and simulator entry points."""

    def __init__(
        self,
        fs,
        system,
        http,
        network,
        watchdog,
        config,
        logger,
        clock,
        boot_manager,
        presence,
        updater,
        device_control,
        module_runtime,
    ):
        self.fs = fs
        self.system = system
        self.http = http
        self.network = network
        self.watchdog = watchdog
        self.config = config
        self.logger = logger
        self.clock = clock
        self.boot_manager = boot_manager
        self.presence = presence
        self.updater = updater
        self.device_control = device_control
        self.module_runtime = module_runtime
        # Set by start() once an OTA check completes, so the control loop doesn't repeat it at once.
        self.ota_checked = False


def create_runtime(
    fs: IFileSystem,
    system: ISystem,
    http: IHttpClient,
    network: INetwork,
    watchdog: IWatchdog,
    config: Config,
    platform: str,
    enable_ota: bool = True,
) -> DeviceRuntime:
    """Wire up the logger and services. ``enable_ota=False`` leaves ``updater`` as None."""
    clock = WallClock(system)
    logger = EdgeLogger(
        system=system,
        http=http,
        device_id=config.device_id,
        api_url=config.api_url,
        api_key=config.api_key,
        logging_config=config.logging,
    )
    boot_manager = BootManager(
        fs=fs,
        system=system,
        max_attempts=config.max_boot_attempts,
        logger=logger,
    )
    presence = PresenceService(http=http, network=network, system=system, config=config, logger=logger)
    updater = None
    if enable_ota:
        updater = Updater(
            fs=fs,
            http=http,
            system=system,
            config=config,
            boot_manager=boot_manager,
            platform=platform,
            logger=logger,
            watchdog=watchdog,
        )
    device_control = DeviceControlClient(http=http, config=config, fs=fs, logger=logger)
    module_runtime = ModuleRuntime(
        system=system,
        device_control=device_control,
        config=config,
        fs=fs,
        logger=logger,
        clock=clock,
    )
    return DeviceRuntime(
        fs=fs,
        system=system,
        http=http,
        network=network,
        watchdog=watchdog,
        config=config,
        logger=logger,
        clock=clock,
        boot_manager=boot_manager,
        presence=presence,
        updater=updater,
        device_control=device_control,
        module_runtime=module_runtime,
    )


def start(runtime: DeviceRuntime) -> None:
    """Run the boot path: connect, register, check OTA, flush markers, mark boot success."""
    config = runtime.config
    logger = runtime.logger
    network = runtime.network

    logger.info("Main startup", {"reset_cause": runtime.system.reset_cause()})
    logger.info("Configuration loaded", {"device_id": config.device_id})

    _connect_network(runtime)
    _feed_watchdog(runtime.watchdog)

    state = runtime.boot_manager.get_state()
    if state.get("current_version"):
        config.current_version = state["current_version"]

    if network.is_connected():
        logger.info("Registering device presence", {"version": config.current_version})
        try:
            runtime.presence.register(config.current_version)
        except Exception as exc:
            logger.warn("Device registration threw exception", {"error": str(exc)})

        _feed_watchdog(runtime.watchdog)
        _check_for_update(runtime)
    else:
        logger.warn("Skipping registration and OTA check while offline")

    if network.is_connected():
        try:
            runtime.module_runtime.flush_pending_timeout_result()
        except Exception as exc:
            logger.warn("Timeout marker flush threw exception", {"error": str(exc)})

    if network.is_connected():
        try:
            runtime.module_runtime.flush_pending_module_status()
        except Exception as exc:
            logger.warn("Module-status marker flush threw exception", {"error": str(exc)})

    _feed_watchdog(runtime.watchdog)
    runtime.boot_manager.mark_success()
    logger.info("Boot path completed, entering control loop")
    logger.flush("startup")


def run(runtime: DeviceRuntime, max_iterations: int | None = None) -> None:
    run_control_loop(
        system=runtime.system,
        presence=runtime.presence,
        device_control=runtime.device_control,
        module_runtime=runtime.module_runtime,
        logger=runtime.logger,
        config=runtime.config,
        network=runtime.network,
        watchdog=runtime.watchdog,
        updater=runtime.updater,
        max_iterations=max_iterations,
        clock=runtime.clock,
        ota_checked=runtime.ota_checked,
    )


def run_device(
    fs: IFileSystem,
    system: ISystem,
    http: IHttpClient,
    network: INetwork,
    watchdog: IWatchdog,
    platform: str,
    config_path: str = CONFIG_PATH,
) -> None:
    """main.py path for real hardware: load config, boot, then run the control loop forever."""
    config = Config.load(fs, path=config_path, system=system)
    runtime = create_runtime(
        fs=fs,
        system=system,
        http=http,
        network=network,
        watchdog=watchdog,
        config=config,
        platform=platform,
    )
    start(runtime)
    run(runtime)


def _connect_network(runtime: DeviceRuntime) -> None:
    config = runtime.config
    logger = runtime.logger
    network = runtime.network

    if config.wifi_country:
        if network.set_country(config.wifi_country):
            logger.info("WiFi country set", {"country": config.wifi_country})
        else:
            logger.warn("WiFi country not applied", {"country": config.wifi_country})

    if not network.set_hostname(config.device_id):
        logger.warn("WiFi hostname not applied", {"device_id": config.device_id})

    logger.info("Attempting WiFi connection", {"ssid": config.wifi_ssid})
    try:
        network.connect(config.wifi_ssid, config.wifi_password)
        logger.info("WiFi connected", {"ip": network.get_ip()})
        if runtime.clock.sync():
            logger.info("NTP time synced")
        else:
            logger.warn("NTP time sync failed; timestamps may be inaccurate")
    except Exception as exc:
        logger.warn("WiFi connection failed; continuing in offline mode", {"error": str(exc)})


def _check_for_update(runtime: DeviceRuntime) -> None:
    logger = runtime.logger
    if runtime.updater is None:
        logger.info("OTA updates disabled; skipping update check")
        return

    logger.info("Checking for OTA updates")
    try:
        update_info = runtime.updater.check()
        runtime.ota_checked = True
    except Exception as exc:
        logger.warn("OTA check threw exception", {"error": str(exc)})
        update_info = None
    _feed_watchdog(runtime.watchdog)
    if update_info is not None:
        logger.info("OTA update will be applied", {"version": update_info.version})
        try:
            runtime.updater.apply(update_info)
        except Exception as exc:
            logger.warn("OTA apply threw exception", {"error": str(exc)})


def _feed_watchdog(watchdog) -> None:
    try:
        watchdog.feed()
    except Exception:
        pass
