from edge.shared.app.dev_command_runtime import execute_dev_command
from edge.shared.tests.mocks.mock_system import MockSystem


class _FakeDeviceControl:
    def __init__(self, report_ok=True):
        self.report_ok = report_ok
        self.calls = []

    def report_dev_command_result(self, command_id, payload):
        self.calls.append((command_id, payload))
        return self.report_ok


class _FakeLogger:
    def __init__(self):
        self.warn_calls = 0

    def warn(self, *_args, **_kwargs):
        self.warn_calls += 1


def test_execute_dev_command_success_reports_result():
    system = MockSystem()
    device_control = _FakeDeviceControl(report_ok=True)

    result = execute_dev_command(
        system=system,
        device_control=device_control,
        command={
            "command_id": "cmd-1",
            "revision_hash": "r1",
            "dedupe_token": "cmd-1:r1",
            "code": "print('hello')",
            "timeout_ms": 5000,
        },
        utc_now_iso=lambda: "2026-05-29T00:00:00Z",
    )

    assert result["status"] == "success"
    assert result["reported"] is True
    assert len(device_control.calls) == 1
    payload = device_control.calls[0][1]
    assert payload["status"] == "success"
    assert payload["stdout"] == "hello"
    assert payload["stderr"] == ""


def test_execute_dev_command_error_reports_stderr():
    system = MockSystem()
    device_control = _FakeDeviceControl(report_ok=True)

    result = execute_dev_command(
        system=system,
        device_control=device_control,
        command={"command_id": "cmd-2", "code": "raise ValueError('boom')", "timeout_ms": 5000},
        utc_now_iso=lambda: "2026-05-29T00:00:00Z",
    )

    assert result["status"] == "error"
    payload = device_control.calls[0][1]
    assert payload["status"] == "error"
    assert "ValueError: boom" in payload["stderr"]


def test_execute_dev_command_timeout_sets_timeout_status():
    system = MockSystem()
    device_control = _FakeDeviceControl(report_ok=True)

    result = execute_dev_command(
        system=system,
        device_control=device_control,
        command={"command_id": "cmd-3", "code": "print('slow')", "timeout_ms": 1},
        utc_now_iso=lambda: "2026-05-29T00:00:00Z",
    )

    assert result["status"] == "timeout"
    payload = device_control.calls[0][1]
    assert payload["status"] == "timeout"
    assert payload["exit_code"] == 124


def test_execute_dev_command_logs_warn_when_report_fails():
    system = MockSystem()
    device_control = _FakeDeviceControl(report_ok=False)
    logger = _FakeLogger()

    result = execute_dev_command(
        system=system,
        device_control=device_control,
        command={"command_id": "cmd-4", "code": "print('x')"},
        logger=logger,
        utc_now_iso=lambda: "2026-05-29T00:00:00Z",
    )

    assert result["reported"] is False
    assert logger.warn_calls >= 1


def test_execute_dev_command_captures_structured_result():
    system = MockSystem()
    device_control = _FakeDeviceControl(report_ok=True)

    result = execute_dev_command(
        system=system,
        device_control=device_control,
        command={
            "command_id": "cmd-5",
            "code": "result = {'temp': 23.5, 'pins': [1, 0, 1]}",
        },
        utc_now_iso=lambda: "2026-05-29T00:00:00Z",
    )

    assert result["status"] == "success"
    payload = device_control.calls[0][1]
    assert payload["data"] == {"temp": 23.5, "pins": [1, 0, 1]}
    assert payload["stdout"] == ""


def test_execute_dev_command_data_is_none_when_result_not_set():
    system = MockSystem()
    device_control = _FakeDeviceControl(report_ok=True)

    result = execute_dev_command(
        system=system,
        device_control=device_control,
        command={"command_id": "cmd-6", "code": "x = 42"},
        utc_now_iso=lambda: "2026-05-29T00:00:00Z",
    )

    payload = device_control.calls[0][1]
    assert payload["data"] is None


def test_execute_dev_command_non_serialisable_result_coerced_to_string():
    system = MockSystem()
    device_control = _FakeDeviceControl(report_ok=True)

    result = execute_dev_command(
        system=system,
        device_control=device_control,
        command={"command_id": "cmd-7", "code": "result = object()"},
        utc_now_iso=lambda: "2026-05-29T00:00:00Z",
    )

    payload = device_control.calls[0][1]
    assert isinstance(payload["data"], str)
    assert "object" in payload["data"]


def test_execute_dev_command_return_value_captured_as_data():
    """Top-level `return` in the code should populate data (the common dev-mode pattern)."""
    system = MockSystem()
    device_control = _FakeDeviceControl(report_ok=True)

    code = (
        "def run(ctx):\n"
        "    return {'raw_value': 128, 'temp_celsius': 53.3}\n"
        "result = run(None)"
    )

    execute_dev_command(
        system=system,
        device_control=device_control,
        command={"command_id": "cmd-8", "code": code},
        utc_now_iso=lambda: "2026-05-29T00:00:00Z",
    )

    payload = device_control.calls[0][1]
    assert payload["status"] == "success"
    assert payload["data"] == {"raw_value": 128, "temp_celsius": 53.3}


def test_execute_dev_command_bare_return_dict():
    """A bare `return {...}` at the top level should work via function wrapping."""
    system = MockSystem()
    device_control = _FakeDeviceControl(report_ok=True)

    code = "return {'raw_value': 128, 'temp_celsius': 53.3}"

    execute_dev_command(
        system=system,
        device_control=device_control,
        command={"command_id": "cmd-9", "code": code},
        utc_now_iso=lambda: "2026-05-29T00:00:00Z",
    )

    payload = device_control.calls[0][1]
    assert payload["status"] == "success"
    assert payload["data"] == {"raw_value": 128, "temp_celsius": 53.3}


def test_execute_dev_command_run_function_auto_called():
    """A `def run(ctx)` function without an explicit call should be invoked automatically."""
    system = MockSystem()
    device_control = _FakeDeviceControl(report_ok=True)

    code = (
        "def run(ctx):\n"
        "    raw_temp = 160\n"
        "    temp_celsius = (raw_temp - 32) * 5 / 9\n"
        "    return {'raw_value': raw_temp, 'temp_celsius': round(temp_celsius, 1)}\n"
    )

    execute_dev_command(
        system=system,
        device_control=device_control,
        command={"command_id": "cmd-10", "code": code},
        utc_now_iso=lambda: "2026-05-29T00:00:00Z",
    )

    payload = device_control.calls[0][1]
    assert payload["status"] == "success"
    assert payload["data"] == {"raw_value": 160, "temp_celsius": 71.1}
