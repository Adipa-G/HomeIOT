import json
from dataclasses import dataclass

from edge.shared.hal.interfaces import IFileSystem


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

    @classmethod
    def load(cls, fs: IFileSystem, path: str = "config.json"):
        raw = fs.read_text(path)
        data = json.loads(raw)

        required = [
            "device_id",
            "api_url",
            "api_key",
            "wifi_ssid",
            "wifi_password",
            "heartbeat_interval_ms",
            "max_boot_attempts",
        ]
        missing = [key for key in required if key not in data]
        if missing:
            raise ValueError("Missing config fields: " + ", ".join(missing))

        return cls(
            device_id=data["device_id"],
            api_url=data["api_url"].rstrip("/"),
            api_key=data["api_key"],
            wifi_ssid=data["wifi_ssid"],
            wifi_password=data["wifi_password"],
            heartbeat_interval_ms=int(data["heartbeat_interval_ms"]),
            max_boot_attempts=int(data["max_boot_attempts"]),
            current_version=data.get("current_version", "0.0.0"),
        )
