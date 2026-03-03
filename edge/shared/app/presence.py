from edge.shared.app.config import Config
from edge.shared.hal.interfaces import IHttpClient, INetwork, ISystem


class PresenceService:
    def __init__(self, http: IHttpClient, network: INetwork, system: ISystem, config: Config):
        self._http = http
        self._network = network
        self._system = system
        self._config = config

    def register(self, version: str) -> bool:
        url = self._config.api_url + "/api/devices/register"
        payload = {
            "device_id": self._config.device_id,
            "version": version,
            "ip": self._network.get_ip(),
            "timestamp": self._system.time_ms(),
        }

        response = self._http.post(url, payload, headers=self._auth_headers())
        return response.status_code in (200, 201)

    def heartbeat(self) -> bool:
        url = self._config.api_url + "/api/devices/heartbeat"
        payload = {
            "device_id": self._config.device_id,
            "timestamp": self._system.time_ms(),
        }

        response = self._http.post(url, payload, headers=self._auth_headers())
        return response.status_code == 200

    def run_heartbeat_loop(self, interval_ms: int, max_iterations=None) -> None:
        count = 0
        while True:
            self.heartbeat()
            count += 1
            if max_iterations is not None and count >= max_iterations:
                return
            self._system.sleep_ms(interval_ms)

    def _auth_headers(self):
        return {
            "X-Device-ID": self._config.device_id,
            "X-Api-Key": self._config.api_key,
        }
