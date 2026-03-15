import json

from edge.shared.app.secret_crypto import decrypt_secret
from edge.shared.hal.interfaces import IFileSystem, ISystem


CONFIG_PATH = "config.json"
CONFIG_PREV_PATH = "config_prev.json"
CONFIG_STAGING_PATH = "config_staging.json"


class LoggingConfig:
    def __init__(
        self,
        enabled_uplink=True,
        buffer_max_bytes=4096,
        flush_interval_ms=30000,
        min_level="INFO",
    ):
        self.enabled_uplink = bool(enabled_uplink)
        self.buffer_max_bytes = int(buffer_max_bytes)
        self.flush_interval_ms = int(flush_interval_ms)
        self.min_level = str(min_level)


class PowerConfig:
    def __init__(
        self,
        enabled=True,
        production_sleep_min_ms=500,
        production_sleep_max_ms=5000,
        development_sleep_min_ms=50,
        development_sleep_max_ms=1000,
        network_retry_base_ms=5000,
        network_retry_max_ms=60000,
        wifi_power_save_enabled=False,
        wifi_power_save_production_mode="modem",
        wifi_power_save_development_mode="none",
    ):
        self.enabled = bool(enabled)
        self.production_sleep_min_ms = int(production_sleep_min_ms)
        self.production_sleep_max_ms = int(production_sleep_max_ms)
        self.development_sleep_min_ms = int(development_sleep_min_ms)
        self.development_sleep_max_ms = int(development_sleep_max_ms)
        self.network_retry_base_ms = int(network_retry_base_ms)
        self.network_retry_max_ms = int(network_retry_max_ms)
        self.wifi_power_save_enabled = bool(wifi_power_save_enabled)
        self.wifi_power_save_production_mode = str(wifi_power_save_production_mode)
        self.wifi_power_save_development_mode = str(wifi_power_save_development_mode)


class Config:
    def __init__(
        self,
        device_id,
        api_url,
        api_key,
        wifi_ssid,
        wifi_password,
        heartbeat_interval_ms,
        max_boot_attempts,
        dev_poll_interval_ms=2000,
        module_assignment_poll_interval_ms=60000,
        current_version="0.0.0",
        logging=None,
        power=None,
    ):
        self.device_id = str(device_id)
        self.api_url = str(api_url)
        self.api_key = str(api_key)
        self.wifi_ssid = str(wifi_ssid)
        self.wifi_password = str(wifi_password)
        self.heartbeat_interval_ms = int(heartbeat_interval_ms)
        self.max_boot_attempts = int(max_boot_attempts)
        self.dev_poll_interval_ms = int(dev_poll_interval_ms)
        self.module_assignment_poll_interval_ms = int(module_assignment_poll_interval_ms)
        self.current_version = str(current_version)
        self.logging = logging or LoggingConfig()
        self.power = power or PowerConfig()

    @classmethod
    def load(cls, fs: IFileSystem, path: str = CONFIG_PATH, system=None):
        raw = fs.read_text(path)
        data = json.loads(raw)

        required = [
            "device_id",
            "api_url",
            "wifi_ssid",
            "heartbeat_interval_ms",
            "max_boot_attempts",
        ]
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError("Missing config fields: " + ", ".join(missing))

        api_key = cls._resolve_secret(data, "api_key", system)
        wifi_password = cls._resolve_secret(data, "wifi_password", system)

        return cls(
            device_id=data["device_id"],
            api_url=data["api_url"].rstrip("/"),
            api_key=api_key,
            wifi_ssid=data["wifi_ssid"],
            wifi_password=wifi_password,
            heartbeat_interval_ms=int(data["heartbeat_interval_ms"]),
            max_boot_attempts=int(data["max_boot_attempts"]),
            dev_poll_interval_ms=max(500, int(data.get("dev_poll_interval_ms", 2000))),
            module_assignment_poll_interval_ms=max(1000, int(data.get("module_assignment_poll_interval_ms", 60000))),
            current_version=data.get("current_version", "0.0.0"),
            logging=cls._load_logging_config(data.get("logging")),
            power=cls._load_power_config(data.get("power")),
        )

    @staticmethod
    def _load_logging_config(payload) -> LoggingConfig:
        if payload is None:
            return LoggingConfig()
        if not isinstance(payload, dict):
            raise ValueError("logging config must be an object")

        return LoggingConfig(
            enabled_uplink=bool(payload.get("enabled_uplink", True)),
            buffer_max_bytes=max(512, int(payload.get("buffer_max_bytes", 4096))),
            flush_interval_ms=max(1000, int(payload.get("flush_interval_ms", 30000))),
            min_level=str(payload.get("min_level", "INFO")).upper(),
        )

    @staticmethod
    def _load_power_config(payload) -> PowerConfig:
        if payload is None:
            return PowerConfig()
        if not isinstance(payload, dict):
            raise ValueError("power config must be an object")

        production_sleep_min_ms = max(50, int(payload.get("production_sleep_min_ms", 500)))
        production_sleep_max_ms = max(production_sleep_min_ms, int(payload.get("production_sleep_max_ms", 5000)))
        development_sleep_min_ms = max(10, int(payload.get("development_sleep_min_ms", 50)))
        development_sleep_max_ms = max(development_sleep_min_ms, int(payload.get("development_sleep_max_ms", 1000)))

        network_retry_base_ms = max(1000, int(payload.get("network_retry_base_ms", 5000)))
        network_retry_max_ms = max(network_retry_base_ms, int(payload.get("network_retry_max_ms", 60000)))

        return PowerConfig(
            enabled=bool(payload.get("enabled", True)),
            production_sleep_min_ms=production_sleep_min_ms,
            production_sleep_max_ms=production_sleep_max_ms,
            development_sleep_min_ms=development_sleep_min_ms,
            development_sleep_max_ms=development_sleep_max_ms,
            network_retry_base_ms=network_retry_base_ms,
            network_retry_max_ms=network_retry_max_ms,
            wifi_power_save_enabled=bool(payload.get("wifi_power_save_enabled", False)),
            wifi_power_save_production_mode=str(payload.get("wifi_power_save_production_mode", "modem")).lower(),
            wifi_power_save_development_mode=str(payload.get("wifi_power_save_development_mode", "none")).lower(),
        )

    @staticmethod
    def _resolve_secret(data: dict, key_name: str, system) -> str:
        plaintext_value = data.get(key_name)
        if plaintext_value is not None:
            return plaintext_value

        enc_key = key_name + "_enc"
        payload = data.get(enc_key)
        if payload is None:
            raise ValueError("Missing config secret: " + key_name)
        if not isinstance(payload, dict):
            raise ValueError("Encrypted secret payload must be an object: " + enc_key)

        bindings = []
        device_id = data.get("device_id")
        if device_id:
            bindings.append(str(device_id))
        if system is not None:
            try:
                unique_id = system.unique_id()
                if unique_id and unique_id not in bindings:
                    bindings.append(unique_id)
            except Exception:
                pass

        for binding_value in bindings:
            try:
                return decrypt_secret(payload, binding_value, key_name)
            except Exception:
                continue

        raise ValueError("Unable to decrypt secret for key: " + key_name)
