from edge.shared.app.config import Config
from edge.shared.app.device_control import DeviceControlClient
from edge.shared.app.module_runtime import ModuleRuntime
from edge.shared.tests.mocks.mock_filesystem import MockFileSystem
from edge.shared.tests.mocks.mock_http_client import MockHttpClient
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


def _post_payloads(http):
    return [call[2] for call in http.calls if call[0] == "POST" and call[1].endswith("/api/devices/modules/results")]


def test_module_runtime_reports_success_with_empty_output_for_no_return():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(system=system, device_control=client, config=config, utc_now_iso=lambda: "2026-05-28T14:30:00Z")

    fs.write_bytes("modules_cache/m1/1.0.0.pkg", b"def run(context):\n    x = 1\n")

    runtime.update_assignment(
        {"modules": [{"module_id": "m1", "version": "1.0.0", "interval_ms": 60000, "timeout_ms": 5000}]},
        now_ms=1000,
    )
    result = runtime.tick(now_ms=1000)

    assert result["executed"] == 1
    payloads = _post_payloads(http)
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["device_id"] == "esp32-001"
    assert payload["module_id"] == "m1"
    assert payload["module_version"] == "1.0.0"
    assert payload["status"] == "success"
    assert payload["output"] == {}
    assert payload["error_message"] is None
    assert payload["started_at_utc"] == "2026-05-28T14:30:00Z"
    assert payload["finished_at_utc"] == "2026-05-28T14:30:00Z"


def test_module_runtime_isolates_failure_and_continues_other_modules():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(system=system, device_control=client, config=config, utc_now_iso=lambda: "2026-05-28T14:30:00Z")

    fs.write_bytes("modules_cache/m-fail/1.0.0.pkg", b"def run(context):\n    raise ValueError('boom')\n")
    fs.write_bytes("modules_cache/m-ok/1.0.0.pkg", b"def run(context):\n    return {'ok': True}\n")

    runtime.update_assignment(
        {
            "modules": [
                {"module_id": "m-fail", "version": "1.0.0", "interval_ms": 60000, "timeout_ms": 5000},
                {"module_id": "m-ok", "version": "1.0.0", "interval_ms": 60000, "timeout_ms": 5000},
            ]
        },
        now_ms=1000,
    )
    result = runtime.tick(now_ms=1000)

    assert result["executed"] == 2
    assert result["success"] == 1
    assert result["failed"] == 1

    payloads = _post_payloads(http)
    assert len(payloads) == 2
    by_id = {payload["module_id"]: payload for payload in payloads}

    assert by_id["m-ok"]["status"] == "success"
    assert by_id["m-ok"]["output"] == {"ok": True}

    assert by_id["m-fail"]["status"] == "error"
    assert by_id["m-fail"]["output"] == {}
    assert "ValueError: boom" in by_id["m-fail"]["error_message"]


def test_module_runtime_respects_independent_intervals():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(system=system, device_control=client, config=config, utc_now_iso=lambda: "2026-05-28T14:30:00Z")

    fs.write_bytes("modules_cache/m-fast/1.0.0.pkg", b"def run(context):\n    return {'kind': 'fast'}\n")
    fs.write_bytes("modules_cache/m-slow/1.0.0.pkg", b"def run(context):\n    return {'kind': 'slow'}\n")

    runtime.update_assignment(
        {
            "modules": [
                {"module_id": "m-fast", "version": "1.0.0", "interval_ms": 60000, "timeout_ms": 5000},
                {"module_id": "m-slow", "version": "1.0.0", "interval_ms": 600000, "timeout_ms": 5000},
            ]
        },
        now_ms=1000,
    )

    first = runtime.tick(now_ms=1000)
    second = runtime.tick(now_ms=61000)

    assert first["executed"] == 2
    assert second["executed"] == 1

    payloads = _post_payloads(http)
    assert len(payloads) == 3
    module_ids = [payload["module_id"] for payload in payloads]
    assert module_ids.count("m-fast") == 2
    assert module_ids.count("m-slow") == 1


def test_module_runtime_marks_timeout_and_resets_device():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(system=system, device_control=client, config=config, utc_now_iso=lambda: "2026-05-28T14:30:00Z")

    fs.write_bytes("modules_cache/m-timeout/1.0.0.pkg", b"def run(context):\n    return {'value': 1}\n")

    runtime.update_assignment(
        {"modules": [{"module_id": "m-timeout", "version": "1.0.0", "interval_ms": 60000, "timeout_ms": 50}]},
        now_ms=1000,
    )
    result = runtime.tick(now_ms=1000)

    assert result["executed"] == 1
    assert result["reset_requested"] is True
    assert system.reset_calls == 1

    payloads = _post_payloads(http)
    assert len(payloads) == 1
    payload = payloads[0]
    assert payload["status"] == "timeout"
    assert payload["output"] == {}
    assert "Module timeout exceeded" in payload["error_message"]


def test_module_runtime_persists_timeout_marker_when_upload_fails():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(system=system, device_control=client, config=config, fs=fs, utc_now_iso=lambda: "2026-05-28T14:30:00Z")

    # Force upload failure for module result posts.
    http.add_json_response("POST", "http://localhost:8000/api/devices/modules/results", 500, {"status": "err"})
    fs.write_bytes("modules_cache/m-timeout/1.0.0.pkg", b"def run(context):\n    return {'value': 1}\n")

    runtime.update_assignment(
        {"modules": [{"module_id": "m-timeout", "version": "1.0.0", "interval_ms": 60000, "timeout_ms": 1}]},
        now_ms=1000,
    )
    runtime.tick(now_ms=1000)

    assert fs.exists("module_timeout_pending.json") is True


def test_module_runtime_flushes_persisted_timeout_marker_when_upload_recovers():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(system=system, device_control=client, config=config, fs=fs, utc_now_iso=lambda: "2026-05-28T14:30:00Z")

    fs.write_text(
        "module_timeout_pending.json",
        '{"device_id":"esp32-001","module_id":"m1","module_version":"1.0.0","run_id":"m1:1.0.0:1000:1","started_at_utc":"2026-05-28T14:30:00Z","finished_at_utc":"2026-05-28T14:30:01Z","elapsed_ms":1000,"status":"timeout","output":{},"error_message":"timeout"}',
    )

    flushed = runtime.flush_pending_timeout_result()

    assert flushed is True
    assert fs.exists("module_timeout_pending.json") is False


# ──────────────────────────── quarantine tests ────────────────────────────


def _status_payloads(http):
    return [call[2] for call in http.calls if call[0] == "POST" and call[1].endswith("/api/devices/modules/status")]


def test_quarantine_count_increments_and_resets_on_success():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(
        system=system, device_control=client, config=config, fs=fs, utc_now_iso=lambda: "2026-05-29T10:00:00Z"
    )

    # First run: fails → count becomes 1
    fs.write_bytes("modules_cache/m1/1.0.0.pkg", b"def run(context):\n    raise RuntimeError('boom')\n")
    runtime.update_assignment(
        {"modules": [{"module_id": "m1", "version": "1.0.0", "interval_ms": 1000, "timeout_ms": 5000}]},
        now_ms=0,
    )
    runtime.tick(now_ms=0)

    import json as _json
    q = _json.loads(fs.read_text("modules_cache/m1/quarantine.json"))
    assert q["failed_start_count"] == 1
    assert q["disabled"] is False

    # Second run: success → quarantine file cleared
    fs.write_bytes("modules_cache/m1/1.0.0.pkg", b"def run(context):\n    return {'ok': True}\n")
    runtime.tick(now_ms=1000)

    assert fs.exists("modules_cache/m1/quarantine.json") is False


def test_quarantine_disables_module_at_threshold():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(
        system=system, device_control=client, config=config, fs=fs,
        utc_now_iso=lambda: "2026-05-29T10:00:00Z", quarantine_threshold=3,
    )

    fs.write_bytes("modules_cache/m-bad/1.0.0.pkg", b"def run(context):\n    raise RuntimeError('crash')\n")
    runtime.update_assignment(
        {"modules": [{"module_id": "m-bad", "version": "1.0.0", "interval_ms": 1000, "timeout_ms": 5000}]},
        now_ms=0,
    )

    # Three consecutive failures
    runtime.tick(now_ms=0)
    runtime.tick(now_ms=1000)
    result = runtime.tick(now_ms=2000)

    import json as _json
    q = _json.loads(fs.read_text("modules_cache/m-bad/quarantine.json"))
    assert q["disabled"] is True
    assert q["failed_start_count"] == 3
    assert "3 consecutive failures" in q["disabled_reason"]

    # Module-status notification was sent to API
    statuses = _status_payloads(http)
    assert len(statuses) == 1
    assert statuses[0]["disabled"] is True
    assert statuses[0]["module_id"] == "m-bad"
    assert statuses[0]["failed_start_count"] == 3

    # Fourth tick: module is skipped, executed == 0
    result = runtime.tick(now_ms=3000)
    assert result["executed"] == 0


def test_quarantine_healthy_module_keeps_running_while_bad_is_disabled():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(
        system=system, device_control=client, config=config, fs=fs,
        utc_now_iso=lambda: "2026-05-29T10:00:00Z", quarantine_threshold=3,
    )

    fs.write_bytes("modules_cache/m-bad/1.0.0.pkg", b"def run(context):\n    raise RuntimeError('crash')\n")
    fs.write_bytes("modules_cache/m-ok/1.0.0.pkg", b"def run(context):\n    return {'ok': True}\n")
    runtime.update_assignment(
        {
            "modules": [
                {"module_id": "m-bad", "version": "1.0.0", "interval_ms": 1000, "timeout_ms": 5000},
                {"module_id": "m-ok", "version": "1.0.0", "interval_ms": 1000, "timeout_ms": 5000},
            ]
        },
        now_ms=0,
    )

    # Drive m-bad to quarantine
    for t in range(3):
        runtime.tick(now_ms=t * 1000)

    # After quarantine, m-ok still executes
    result = runtime.tick(now_ms=3000)
    assert result["executed"] == 1
    assert result["success"] == 1
    payloads = _post_payloads(http)
    last_module_ids = [p["module_id"] for p in payloads[-1:]]
    assert "m-ok" in [p["module_id"] for p in payloads]


def test_quarantine_clears_on_version_change():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(
        system=system, device_control=client, config=config, fs=fs,
        utc_now_iso=lambda: "2026-05-29T10:00:00Z", quarantine_threshold=2,
    )

    fs.write_bytes("modules_cache/m1/1.0.0.pkg", b"def run(context):\n    raise RuntimeError('v1 bad')\n")
    runtime.update_assignment(
        {"modules": [{"module_id": "m1", "version": "1.0.0", "interval_ms": 1000, "timeout_ms": 5000}]},
        now_ms=0,
    )
    runtime.tick(now_ms=0)
    runtime.tick(now_ms=1000)

    import json as _json
    q = _json.loads(fs.read_text("modules_cache/m1/quarantine.json"))
    assert q["disabled"] is True

    # Deploy new version → quarantine should be cleared
    fs.write_bytes("modules_cache/m1/2.0.0.pkg", b"def run(context):\n    return {'ok': True}\n")
    runtime.update_assignment(
        {"modules": [{"module_id": "m1", "version": "2.0.0", "interval_ms": 1000, "timeout_ms": 5000}]},
        now_ms=2000,
    )

    assert fs.exists("modules_cache/m1/quarantine.json") is False

    result = runtime.tick(now_ms=2000)
    assert result["executed"] == 1
    assert result["success"] == 1


def test_quarantine_auto_clears_in_tick_on_version_change():
    """If quarantine file persists with a stale version, tick() auto-clears and runs the module."""
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(
        system=system, device_control=client, config=config, fs=fs,
        utc_now_iso=lambda: "2026-05-29T10:00:00Z", quarantine_threshold=2,
    )

    # Manually write a quarantine file for version 1.0.0
    import json as _json
    fs.makedirs("modules_cache/m1")
    fs.write_text("modules_cache/m1/quarantine.json", _json.dumps({
        "failed_start_count": 5,
        "disabled": True,
        "disabled_reason": "threshold exceeded",
        "last_version": "1.0.0",
    }))

    # Deploy version 2.0.0 — simulates post-reboot with new version
    fs.write_bytes("modules_cache/m1/2.0.0.pkg", b"def run(context):\n    return {'ok': True}\n")
    runtime.update_assignment(
        {"modules": [{"module_id": "m1", "version": "2.0.0", "interval_ms": 1000, "timeout_ms": 5000}]},
        now_ms=0,
    )

    # Even if quarantine file somehow persisted, tick should auto-clear because version changed
    # Re-write quarantine to simulate it surviving (e.g. concurrent write race)
    fs.write_text("modules_cache/m1/quarantine.json", _json.dumps({
        "failed_start_count": 5,
        "disabled": True,
        "disabled_reason": "threshold exceeded",
        "last_version": "1.0.0",
    }))

    result = runtime.tick(now_ms=0)
    assert result["executed"] == 1
    assert result["success"] == 1


def test_quarantine_module_status_persisted_when_api_offline():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(
        system=system, device_control=client, config=config, fs=fs,
        utc_now_iso=lambda: "2026-05-29T10:00:00Z", quarantine_threshold=2,
    )

    # Make module-status endpoint fail
    http.add_json_response("POST", "http://localhost:8000/api/devices/modules/status", 503, {"error": "unavailable"})

    fs.write_bytes("modules_cache/m1/1.0.0.pkg", b"def run(context):\n    raise RuntimeError('crash')\n")
    runtime.update_assignment(
        {"modules": [{"module_id": "m1", "version": "1.0.0", "interval_ms": 1000, "timeout_ms": 5000}]},
        now_ms=0,
    )
    runtime.tick(now_ms=0)
    runtime.tick(now_ms=1000)

    assert fs.exists("module_status_pending.json") is True

    import json as _json
    pending = _json.loads(fs.read_text("module_status_pending.json"))
    assert pending["module_id"] == "m1"
    assert pending["disabled"] is True


def test_quarantine_flush_pending_module_status_on_recovery():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(
        system=system, device_control=client, config=config, fs=fs,
        utc_now_iso=lambda: "2026-05-29T10:00:00Z",
    )

    import json as _json
    pending = {
        "device_id": "esp32-001",
        "module_id": "m1",
        "module_version": "1.0.0",
        "disabled": True,
        "disabled_reason": "Failed start count exceeded threshold (3 consecutive failures)",
        "failed_start_count": 3,
        "disabled_at_utc": "2026-05-29T10:00:00Z",
    }
    fs.write_text("module_status_pending.json", _json.dumps(pending))

    flushed = runtime.flush_pending_module_status()

    assert flushed is True
    assert fs.exists("module_status_pending.json") is False
    statuses = _status_payloads(http)
    assert len(statuses) == 1
    assert statuses[0]["module_id"] == "m1"


def test_quarantine_reenable_via_assignment_clears_disabled_state():
    fs = MockFileSystem()
    http = MockHttpClient()
    system = MockSystem()
    config = _config()
    client = DeviceControlClient(http=http, config=config, fs=fs)
    runtime = ModuleRuntime(
        system=system, device_control=client, config=config, fs=fs,
        utc_now_iso=lambda: "2026-05-29T10:00:00Z", quarantine_threshold=2,
    )

    import json as _json
    # Pre-seed quarantine state as disabled
    q = {"failed_start_count": 2, "disabled": True, "disabled_reason": "threshold", "disabled_at_utc": "2026-05-29T09:00:00Z", "last_version": "1.0.0"}
    fs.write_text("modules_cache/m1/quarantine.json", _json.dumps(q))

    fs.write_bytes("modules_cache/m1/1.0.0.pkg", b"def run(context):\n    return {'ok': True}\n")
    runtime.update_assignment(
        {"modules": [{"module_id": "m1", "version": "1.0.0", "interval_ms": 1000, "timeout_ms": 5000, "enabled": True}]},
        now_ms=0,
    )

    # Quarantine file should be cleared
    assert fs.exists("modules_cache/m1/quarantine.json") is False

    # Module runs successfully on next tick
    result = runtime.tick(now_ms=0)
    assert result["executed"] == 1
    assert result["success"] == 1

    # Re-enable acknowledgement was sent to API
    statuses = _status_payloads(http)
    assert len(statuses) == 1
    assert statuses[0]["disabled"] is False
    assert statuses[0]["module_id"] == "m1"
