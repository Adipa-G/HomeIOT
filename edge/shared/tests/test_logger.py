from edge.shared.app.config import LoggingConfig
from edge.shared.app.endpoints import LOGS_PATH
from edge.shared.app.logger import EdgeLogger
from edge.shared.tests.mocks.mock_http_client import MockHttpClient


class ControlledSystem:
    def __init__(self):
        self.now = 0

    def reset(self):
        return None

    def unique_id(self):
        return "mock-device-id"

    def time_ms(self):
        self.now += 100
        return self.now

    def sleep_ms(self, milliseconds):
        self.now += milliseconds


def test_logger_flushes_on_threshold():
    system = ControlledSystem()
    http = MockHttpClient()
    cfg = LoggingConfig(
        enabled_uplink=True,
        buffer_max_bytes=120,
        flush_interval_ms=30000,
        min_level="INFO",
    )
    logger = EdgeLogger(
        system=system,
        http=http,
        device_id="esp32-001",
        api_url="http://localhost:8000",
        api_key="secret",
        logging_config=cfg,
    )

    logger.info("event-1")
    logger.info("event-2")
    logger.info("event-3")

    post_calls = [call for call in http.calls if call[0] == "POST" and call[1].endswith(LOGS_PATH)]
    assert len(post_calls) >= 1


def test_logger_flushes_on_interval_tick():
    system = ControlledSystem()
    http = MockHttpClient()
    cfg = LoggingConfig(
        enabled_uplink=True,
        buffer_max_bytes=4096,
        flush_interval_ms=150,
        min_level="INFO",
    )
    logger = EdgeLogger(
        system=system,
        http=http,
        device_id="esp32-001",
        api_url="http://localhost:8000",
        api_key="secret",
        logging_config=cfg,
    )

    logger.info("single-event")
    logger.tick()

    post_calls = [call for call in http.calls if call[0] == "POST" and call[1].endswith(LOGS_PATH)]
    assert len(post_calls) == 1


def test_logger_drops_newest_when_buffer_full_and_reports_truncation():
    system = ControlledSystem()
    http = MockHttpClient()

    http.add_json_response("POST", "http://localhost:8000" + LOGS_PATH, 500, {"ok": False})

    cfg = LoggingConfig(
        enabled_uplink=True,
        buffer_max_bytes=300,
        flush_interval_ms=30000,
        min_level="INFO",
    )
    logger = EdgeLogger(
        system=system,
        http=http,
        device_id="esp32-001",
        api_url="http://localhost:8000",
        api_key="secret",
        logging_config=cfg,
    )

    logger.info("A" * 120)
    logger.info("B" * 120)
    logger.info("C" * 120)
    logger.info("D" * 120)

    # Switch endpoint to success and flush; payload should include truncation metadata.
    http.add_json_response("POST", "http://localhost:8000" + LOGS_PATH, 200, {"ok": True})
    ok = logger.flush("manual")

    assert ok is True
    method, url, data, _headers = http.calls[-1]
    assert method == "POST"
    assert url == "http://localhost:8000" + LOGS_PATH
    assert data["truncated"] is True
    assert data["dropped_count"] > 0


def test_logger_prints_console_event_with_context(capsys):
    system = ControlledSystem()
    cfg = LoggingConfig(
        enabled_uplink=False,
        buffer_max_bytes=4096,
        flush_interval_ms=30000,
        min_level="INFO",
    )
    logger = EdgeLogger(system=system, logging_config=cfg)

    logger.warn("boot warning", {"reason": "watchdog unavailable", "attempts": 8})

    captured = capsys.readouterr().out.strip()
    assert "boot warning" in captured
    assert "watchdog unavailable" in captured


def test_logger_flush_returns_false_on_transport_exception():
    class FailingHttpClient:
        def post(self, url, data, headers=None):
            raise OSError(113)

    system = ControlledSystem()
    cfg = LoggingConfig(
        enabled_uplink=True,
        buffer_max_bytes=4096,
        flush_interval_ms=30000,
        min_level="INFO",
    )
    logger = EdgeLogger(
        system=system,
        http=FailingHttpClient(),
        device_id="esp32-001",
        api_url="http://localhost:8000",
        api_key="secret",
        logging_config=cfg,
    )

    logger.info("startup")

    assert logger.flush("startup") is False


def test_logger_buffer_stores_as_bytearray():
    """Compact buffer stores events as newline-delimited JSON in a bytearray."""
    system = ControlledSystem()
    cfg = LoggingConfig(
        enabled_uplink=True,
        buffer_max_bytes=4096,
        flush_interval_ms=30000,
        min_level="INFO",
    )
    logger = EdgeLogger(
        system=system,
        http=MockHttpClient(),
        device_id="esp32-001",
        api_url="http://localhost:8000",
        api_key="secret",
        logging_config=cfg,
    )

    logger.info("event-one", {"key": "value"})
    logger.warn("event-two")

    assert isinstance(logger._buffer_data, bytearray)
    assert len(logger._buffer_data) > 0

    decoded = logger._decode_buffer()
    assert len(decoded) == 2
    assert decoded[0]["message"] == "event-one"
    assert decoded[0]["context"]["key"] == "value"
    assert decoded[1]["level"] == "WARN"


def test_logger_flush_clears_bytearray_buffer():
    """After a successful flush the buffer is empty."""
    system = ControlledSystem()
    http = MockHttpClient()
    cfg = LoggingConfig(
        enabled_uplink=True,
        buffer_max_bytes=4096,
        flush_interval_ms=30000,
        min_level="INFO",
    )
    logger = EdgeLogger(
        system=system,
        http=http,
        device_id="esp32-001",
        api_url="http://localhost:8000",
        api_key="secret",
        logging_config=cfg,
    )

    logger.info("before-flush")
    assert len(logger._buffer_data) > 0

    ok = logger.flush("manual")
    assert ok is True
    assert len(logger._buffer_data) == 0
    assert logger._entry_count == 0

    # Verify payload sent contains the log entry
    post_calls = [c for c in http.calls if c[0] == "POST"]
    assert len(post_calls) >= 1
    payload = post_calls[-1][2]
    assert len(payload["logs"]) == 1
    assert payload["logs"][0]["message"] == "before-flush"


def test_logger_pause_uplink_prevents_flush():
    """Pausing uplink returns False from flush without sending."""
    system = ControlledSystem()
    http = MockHttpClient()
    cfg = LoggingConfig(
        enabled_uplink=True,
        buffer_max_bytes=4096,
        flush_interval_ms=30000,
        min_level="INFO",
    )
    logger = EdgeLogger(
        system=system,
        http=http,
        device_id="esp32-001",
        api_url="http://localhost:8000",
        api_key="secret",
        logging_config=cfg,
    )

    logger.info("some-event")
    logger.pause_uplink()
    assert logger.flush("manual") is False

    logger.resume_uplink()
    assert logger.flush("manual") is True
