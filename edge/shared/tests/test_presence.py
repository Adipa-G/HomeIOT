from edge.shared.app.config import Config
from edge.shared.app.presence import PresenceService
from edge.shared.tests.mocks.mock_http_client import MockHttpClient
from edge.shared.tests.mocks.mock_network import MockNetwork
from edge.shared.tests.mocks.mock_system import MockSystem


def _config():
    return Config(
        device_id="esp32-001",
        api_url="http://localhost:8000",
        api_key="secret",
        wifi_ssid="ssid",
        wifi_password="pass",
        heartbeat_interval_ms=1000,
        max_boot_attempts=3,
        current_version="1.0.0",
    )


def test_register_sends_expected_payload_and_headers():
    http = MockHttpClient()
    network = MockNetwork(ip="192.168.1.30")
    system = MockSystem()
    service = PresenceService(http=http, network=network, system=system, config=_config())

    ok = service.register("1.0.0")

    assert ok is True
    method, url, data, headers = http.calls[0]
    assert method == "POST"
    assert url == "http://localhost:8000/api/devices/register"
    assert data["device_id"] == "esp32-001"
    assert data["ip"] == "192.168.1.30"
    assert headers["X-Device-ID"] == "esp32-001"
    assert headers["X-Api-Key"] == "secret"


def test_heartbeat_posts_device_identity():
    http = MockHttpClient()
    network = MockNetwork()
    system = MockSystem()
    service = PresenceService(http=http, network=network, system=system, config=_config())

    ok = service.heartbeat()

    assert ok is True
    method, url, data, headers = http.calls[0]
    assert method == "POST"
    assert url == "http://localhost:8000/api/devices/heartbeat"
    assert data["device_id"] == "esp32-001"
    assert "uptime_ms" in data
    assert "free_memory_bytes" in data
    assert data["free_memory_bytes"] == 65536
    assert headers["X-Device-ID"] == "esp32-001"
    assert headers["X-Api-Key"] == "secret"


def test_heartbeat_with_metadata_returns_payload():
    http = MockHttpClient()
    network = MockNetwork()
    system = MockSystem()
    service = PresenceService(http=http, network=network, system=system, config=_config())

    http.add_json_response("POST", "http://localhost:8000/api/devices/heartbeat", 200, {"mode": "development"})

    payload = service.heartbeat_with_metadata()

    assert payload["mode"] == "development"


def test_heartbeat_loop_runs_multiple_iterations():
    http = MockHttpClient()
    network = MockNetwork()
    system = MockSystem()
    service = PresenceService(http=http, network=network, system=system, config=_config())

    service.run_heartbeat_loop(interval_ms=1500, max_iterations=3)

    assert len(http.calls) == 3
    assert system.sleep_calls == [1500, 1500]
