import json

from edge.bootstrap.provisioning import build_device_config
from edge.shared.app.boot_manager import BootManager
from edge.shared.app.config import CONFIG_PATH, Config
from edge.shared.app.safe_io import atomic_write_text
from edge.shared.app.updater import Updater


WIFI_CONNECT_ATTEMPTS = 3
WIFI_RETRY_DELAY_MS = 5000
REQUIRED_PROVISION_KEYS = ("device_id", "platform", "api_url", "api_key", "wifi_ssid", "wifi_password")
# getaddrinfo failures: -2 on RP2040 (EAI_NONAME), -202 on ESP32 lwIP.
DNS_LOOKUP_ERRORS = (-2, -202)


class ConsoleLogger:
    def info(self, message, context=None):
        self._write("INFO", message, context)

    def warn(self, message, context=None):
        self._write("WARN", message, context)

    def error(self, message, context=None):
        self._write("ERROR", message, context)

    def flush(self, reason=None):
        pass

    @staticmethod
    def _write(level, message, context):
        if context:
            print("[bootstrap] " + level + " " + message + " " + json.dumps(context))
        else:
            print("[bootstrap] " + level + " " + message)


def create_device_services():
    """Instantiate the shared MicroPython HAL used by the real firmware."""
    from edge.shared.hal.filesystem import MicroPythonFileSystem
    from edge.shared.hal.http_client import MicroPythonHttpClient
    from edge.shared.hal.network import MicroPythonNetwork
    from edge.shared.hal.system import MicroPythonSystem

    return MicroPythonFileSystem(), MicroPythonSystem(), MicroPythonNetwork(), MicroPythonHttpClient()


def write_config(fs, provision, template):
    missing = [key for key in REQUIRED_PROVISION_KEYS if key not in provision]
    if missing:
        raise ValueError("Missing provisioning fields: " + ", ".join(missing))

    config = build_device_config(
        template,
        device_id=provision["device_id"],
        api_url=provision["api_url"],
        api_key=provision["api_key"],
        wifi_ssid=provision["wifi_ssid"],
        wifi_password=provision["wifi_password"],
    )
    atomic_write_text(fs, CONFIG_PATH, json.dumps(config))


def connect_wifi(network, system, config, logger, attempts=WIFI_CONNECT_ATTEMPTS):
    last_error = None
    for attempt in range(1, attempts + 1):
        logger.info("Connecting to WiFi", {"ssid": config.wifi_ssid, "attempt": attempt})
        try:
            network.connect(config.wifi_ssid, config.wifi_password)
            if network.is_connected():
                logger.info("WiFi connected", {"ip": network.get_ip()})
                return
        except Exception as exc:
            last_error = exc
            logger.warn("WiFi connection failed", {"error": str(exc)})
        if attempt < attempts:
            system.sleep_ms(WIFI_RETRY_DELAY_MS)
    raise RuntimeError("Unable to connect to WiFi: " + str(last_error))


def run_bootstrap(fs, system, network, http, provision, template, logger=None):
    """Write config.json, then install the latest release through the regular OTA updater.

    On success Updater.apply() overwrites main.py/boot.py with the firmware
    versions and resets the device, so this function does not return on hardware.
    """
    logger = logger or ConsoleLogger()
    logger.info("Bootstrap started", {"device_id": provision.get("device_id"), "platform": provision.get("platform")})

    write_config(fs, provision, template)
    config = Config.load(fs, system=system)
    logger.info("Config written", {"path": CONFIG_PATH})

    connect_wifi(network, system, config, logger)
    try:
        system.sync_time()
    except Exception:
        pass

    boot_manager = BootManager(fs=fs, system=system, max_attempts=config.max_boot_attempts, logger=logger)
    updater = Updater(
        fs=fs,
        http=http,
        system=system,
        config=config,
        boot_manager=boot_manager,
        platform=provision["platform"],
        logger=logger,
    )

    try:
        update_info = updater.check()
    except OSError as exc:
        if exc.args and exc.args[0] in DNS_LOOKUP_ERRORS:
            raise RuntimeError(
                "Cannot resolve the API host in " + config.api_url + ". The device uses your router's DNS, "
                "which may not know local machine names; re-provision with an IP address "
                "(e.g. http://192.168.1.10:8080) or a fully qualified hostname."
            )
        raise
    if update_info is None:
        raise RuntimeError(
            "No firmware release received. Check the API URL, that the device is registered "
            "and that a release exists for platform " + str(provision["platform"])
        )

    logger.info("Installing firmware", {"version": update_info.version})
    updater.apply(update_info)
