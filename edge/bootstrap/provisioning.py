from edge.shared.app.secret_crypto import SCHEME, encrypt_secret


DEFAULT_LOGGING = {
    "enabled_uplink": True,
    "buffer_max_bytes": 4096,
    "flush_interval_ms": 30000,
    "min_level": "INFO",
}


def build_device_config(
    template,
    device_id,
    api_url,
    api_key,
    wifi_ssid,
    wifi_password,
    current_version="0.0.0",
    heartbeat_interval_ms=None,
    max_boot_attempts=None,
):
    """Return a device config dict built from a platform config template.

    Secrets are encrypted with the device id as binding so plaintext never
    lands in config.json. Used by the first-boot bootstrap on the device.
    """
    config = dict(template)
    config["device_id"] = str(device_id)
    config["api_url"] = str(api_url).rstrip("/")
    config.pop("api_key", None)
    config.pop("wifi_password", None)
    config["api_key_enc"] = encrypt_secret(str(api_key), config["device_id"], "api_key")
    config["wifi_ssid"] = str(wifi_ssid)
    config["wifi_password_enc"] = encrypt_secret(str(wifi_password), config["device_id"], "wifi_password")
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
