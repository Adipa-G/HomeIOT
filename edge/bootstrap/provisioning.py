from edge.shared.app.config import normalize_wifi_country
from edge.shared.app.secret_crypto import SCHEME, encrypt_secret

TYPE_CHECKING = False
if TYPE_CHECKING:  # never true on a device; see edge/shared/hal/interfaces.py
    from typing import Any


DEFAULT_LOGGING = {
    "enabled_uplink": True,
    "buffer_max_bytes": 4096,
    "flush_interval_ms": 30000,
    "min_level": "INFO",
}


def build_device_config(
    template: "dict[str, Any]",
    device_id: str,
    api_url: str,
    api_key: str,
    wifi_ssid: str,
    wifi_password: str,
    current_version: str = "0.0.0",
    heartbeat_interval_ms: int | None = None,
    max_boot_attempts: int | None = None,
    wifi_country: str | None = None,
) -> "dict[str, Any]":
    """Return a device config dict built from a platform config template.

    Secrets are encrypted with the device id as binding so plaintext never
    lands in config.json. Used by the first-boot bootstrap on the device.
    """
    config: "dict[str, Any]" = dict(template)
    config["device_id"] = str(device_id)
    config["api_url"] = str(api_url).rstrip("/")
    config.pop("api_key", None)
    config.pop("wifi_password", None)
    config["api_key_enc"] = encrypt_secret(str(api_key), config["device_id"], "api_key")
    config["wifi_ssid"] = str(wifi_ssid)
    config["wifi_password_enc"] = encrypt_secret(str(wifi_password), config["device_id"], "wifi_password")
    # Written explicitly so OTA merges keep it as a per-device value.
    config["wifi_country"] = normalize_wifi_country(
        wifi_country if wifi_country else config.get("wifi_country")
    )
    if heartbeat_interval_ms is not None:
        config["heartbeat_interval_ms"] = int(heartbeat_interval_ms)
    if max_boot_attempts is not None:
        config["max_boot_attempts"] = int(max_boot_attempts)
    config["current_version"] = str(current_version)
    if not isinstance(config.get("logging"), dict):
        config["logging"] = dict(DEFAULT_LOGGING)
    config["security"] = {
        "binding": "device_id",
        "scheme": SCHEME,
    }
    return config
