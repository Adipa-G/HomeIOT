import json
from dataclasses import dataclass, field
from typing import Optional

from edge.shared.app.secret_crypto import decrypt_secret
from edge.shared.hal.interfaces import IFileSystem, ISystem


CONFIG_PATH = "config.json"
CONFIG_PREV_PATH = "config_prev.json"
CONFIG_STAGING_PATH = "config_staging.json"


@dataclass
class LoggingConfig:
    enabled_uplink: bool = True
    buffer_max_bytes: int = 4096
    flush_interval_ms: int = 30000
    min_level: str = "INFO"


@dataclass
class Config:
    device_id: str
    api_url: str
    api_key: str
    wifi_ssid: str
    wifi_password: str
    heartbeat_interval_ms: int
    max_boot_attempts: int
    current_version: str = "0.0.0"
    logging: LoggingConfig = field(default_factory=LoggingConfig)

    @classmethod
    def load(cls, fs: IFileSystem, path: str = CONFIG_PATH, system: Optional[ISystem] = None):
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
            current_version=data.get("current_version", "0.0.0"),
            logging=cls._load_logging_config(data.get("logging")),
        )

    @staticmethod
    def _load_logging_config(payload: Optional[dict]) -> LoggingConfig:
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
    def _resolve_secret(data: dict, key_name: str, system: Optional[ISystem]) -> str:
        plaintext_value = data.get(key_name)
        if plaintext_value is not None:
            return plaintext_value

        enc_key = key_name + "_enc"
        payload = data.get(enc_key)
        if payload is None:
            raise ValueError("Missing config secret: " + key_name)
        if not isinstance(payload, dict):
            raise ValueError("Encrypted secret payload must be an object: " + enc_key)
        if system is None:
            raise ValueError("Encrypted secret requires system identity: " + enc_key)

        try:
            binding_value = system.unique_id()
            return decrypt_secret(payload, binding_value, key_name)
        except Exception as exc:
            raise ValueError("Unable to decrypt secret for key: " + key_name) from exc
