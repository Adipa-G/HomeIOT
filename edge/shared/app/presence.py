import json

from edge.shared.app.config import Config
from edge.shared.app.endpoints import HEARTBEAT_PATH, REGISTER_DEVICE_PATH
from edge.shared.hal.interfaces import IHttpClient, INetwork, ISystem


class PresenceService:
    def __init__(self, http: IHttpClient, network: INetwork, system: ISystem, config: Config, logger=None):
        self._http = http
        self._network = network
        self._system = system
        self._config = config
        self._logger = logger

    def register(self, version: str) -> bool:
        url = self._config.api_url + REGISTER_DEVICE_PATH
        payload = {
            "device_id": self._config.device_id,
            "version": version,
            "ip": self._network.get_ip(),
            "timestamp": self._system.time_ms(),
        }

        self._log_info("Sending registration", {"url": url, "version": version})

        response = self._http.post(url, payload, headers=self._auth_headers())
        ok = response.status_code in (200, 201)
        if ok:
            self._log_info("Device registered", {"version": version, "ip": payload["ip"]})
        else:
            self._log_warn("Device registration failed", {"status_code": response.status_code})
        return ok

    def heartbeat(self) -> bool:
        response = self._post_heartbeat()
        ok = response.status_code == 200
        if not ok:
            self._log_warn("Heartbeat failed", {"status_code": response.status_code})
        return ok

    def heartbeat_with_metadata(self):
        response = self._post_heartbeat()
        if response.status_code != 200:
            self._log_warn("Heartbeat failed", {"status_code": response.status_code})
            return None
        try:
            return json.loads(response.text) if response.text else {}
        except Exception:
            self._log_warn("Heartbeat metadata parse failed")
            return {}

    def _post_heartbeat(self):
        url = self._config.api_url + HEARTBEAT_PATH
        payload = {
            "device_id": self._config.device_id,
            "timestamp": self._system.time_ms(),
        }

        self._log_info("Sending heartbeat", {"url": url})
        return self._http.post(url, payload, headers=self._auth_headers())

    def run_heartbeat_loop(self, interval_ms: int, max_iterations=None) -> None:
        count = 0
        self._log_info("Heartbeat loop started", {"interval_ms": interval_ms})
        while True:
            self.heartbeat()
            count += 1
            if max_iterations is not None and count >= max_iterations:
                self._log_info("Heartbeat loop completed", {"iterations": count})
                return
            if self._logger is not None:
                self._logger.tick()
            self._system.sleep_ms(interval_ms)

    def _auth_headers(self):
        return {
            "X-Device-ID": self._config.device_id,
            "X-Api-Key": self._config.api_key,
        }

    def _log_info(self, message: str, context=None) -> None:
        if self._logger is not None:
            self._logger.info(message, context)

    def _log_warn(self, message: str, context=None) -> None:
        if self._logger is not None:
            self._logger.warn(message, context)
