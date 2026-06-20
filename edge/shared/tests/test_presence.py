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


# Tests for heartbeat failure reboot feature
def test_heartbeat_failure_counter_increments_on_failure():
    http = MockHttpClient()
    network = MockNetwork()
    system = MockSystem()
    service = PresenceService(http=http, network=network, system=system, config=_config())

    # Mock failure responses
    http.add_json_response("POST", "http://localhost:8000/api/devices/heartbeat", 500, {})

    assert service.consecutive_heartbeat_failures == 0

    # First failure
    service.heartbeat()
    assert service.consecutive_heartbeat_failures == 1

    # Second failure
    service.heartbeat()
    assert service.consecutive_heartbeat_failures == 2

    # Third failure
    service.heartbeat()
    assert service.consecutive_heartbeat_failures == 3


def test_heartbeat_failure_counter_resets_on_success():
    http = MockHttpClient()
    network = MockNetwork()
    system = MockSystem()
    service = PresenceService(http=http, network=network, system=system, config=_config())

    # Mock failure response first
    http.add_json_response("POST", "http://localhost:8000/api/devices/heartbeat", 500, {})
    service.heartbeat()
    service.heartbeat()
    service.heartbeat()
    assert service.consecutive_heartbeat_failures == 3

    # Now mock success response
    http._responses.clear()
    http.add_json_response("POST", "http://localhost:8000/api/devices/heartbeat", 200, {})

    service.heartbeat()
    assert service.consecutive_heartbeat_failures == 0

    # Failures should start counting again from 0
    http._responses.clear()
    http.add_json_response("POST", "http://localhost:8000/api/devices/heartbeat", 500, {})
    service.heartbeat()
    assert service.consecutive_heartbeat_failures == 1


def test_heartbeat_triggers_reboot_at_10_consecutive_failures():
    http = MockHttpClient()
    network = MockNetwork()
    system = MockSystem()
    service = PresenceService(http=http, network=network, system=system, config=_config())

    # Mock failure responses
    http.add_json_response("POST", "http://localhost:8000/api/devices/heartbeat", 500, {})

    # 9 failures should not trigger reset
    for i in range(9):
        service.heartbeat()
    assert service.consecutive_heartbeat_failures == 9
    assert system.reset_calls == 0

    # 10th failure should trigger reset
    service.heartbeat()
    assert service.consecutive_heartbeat_failures == 10
    assert system.reset_calls == 1


def test_heartbeat_does_not_trigger_multiple_resets_after_threshold():
    http = MockHttpClient()
    network = MockNetwork()
    system = MockSystem()
    service = PresenceService(http=http, network=network, system=system, config=_config())

    # Mock failure responses
    http.add_json_response("POST", "http://localhost:8000/api/devices/heartbeat", 500, {})

    # Trigger reboot at 10 failures
    for i in range(10):
        service.heartbeat()
    assert system.reset_calls == 1

    # Additional failures should not trigger more resets
    service.heartbeat()
    service.heartbeat()
    assert system.reset_calls == 1  # Should still be 1


def test_heartbeat_counter_starts_at_zero():
    http = MockHttpClient()
    network = MockNetwork()
    system = MockSystem()
    service = PresenceService(http=http, network=network, system=system, config=_config())

    assert service.consecutive_heartbeat_failures == 0

