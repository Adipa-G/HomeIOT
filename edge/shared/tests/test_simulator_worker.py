"""Tests for the PC simulator entry point."""
import json
import sys

import pytest

from edge.shared.app import startup
from edge.shared.app.endpoints import OTA_CHECK_PATH
from edge.shared.hal.interfaces import HttpResponse
from edge.simulator import worker


class _RecordingHttp:
    def __init__(self):
        self.urls = []

    def get(self, url, headers=None):
        self.urls.append(url)
        return HttpResponse(status_code=204, text="", content=b"")

    def post(self, url, data, headers=None, timeout_s=None):
        self.urls.append(url)
        return HttpResponse(status_code=200, text="{}", content=b"{}")

    def get_stream(self, url, headers=None):
        raise AssertionError("simulator must not stream OTA releases")


def _write_config(path):
    path.write_text(
        json.dumps(
            {
                "device_id": "simulator-device-1",
                "api_url": "http://localhost:5228",
                "api_key": "simulator-api-key",
                "wifi_ssid": "HomeNetwork",
                "wifi_password": "pw",
                "heartbeat_interval_ms": 30000,
                "max_boot_attempts": 3,
                "current_version": "1.0.0",
                "logging": {"enabled_uplink": False},
            }
        )
    )


@pytest.fixture(autouse=True)
def _no_signal_handlers(monkeypatch):
    monkeypatch.setattr(worker, "_setup_signal_handlers", lambda: None)


def test_run_simulator_uses_shared_startup_with_ota_disabled_and_cli_overrides(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _write_config(config_path)
    calls = {}
    sentinel = object()

    def _create_runtime(**kwargs):
        calls["create"] = kwargs
        return sentinel

    monkeypatch.setattr(startup, "create_runtime", _create_runtime)
    monkeypatch.setattr(startup, "start", lambda runtime: calls.setdefault("start", runtime))
    monkeypatch.setattr(
        startup, "run", lambda runtime, max_iterations=None: calls.setdefault("run", (runtime, max_iterations))
    )

    worker.run_simulator(
        config_path=str(config_path),
        device_id="sim-override",
        api_url="http://api:1",
        api_key="override-key",
        max_iterations=3,
    )

    created = calls["create"]
    assert created["platform"] == "simulator"
    assert created["enable_ota"] is False
    assert created["config"].device_id == "sim-override"
    assert created["config"].api_url == "http://api:1"
    assert created["config"].api_key == "override-key"
    assert calls["start"] is sentinel
    assert calls["run"] == (sentinel, 3)


def test_run_simulator_exits_with_error_when_startup_fails(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _write_config(config_path)

    def _boom(**_kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(startup, "create_runtime", _boom)

    with pytest.raises(SystemExit) as exc_info:
        worker.run_simulator(config_path=str(config_path))

    assert exc_info.value.code == 1


def test_run_simulator_exits_when_requests_is_missing(tmp_path, monkeypatch):
    config_path = tmp_path / "config.json"
    _write_config(config_path)
    monkeypatch.setitem(sys.modules, "requests", None)
    created = []
    monkeypatch.setattr(startup, "create_runtime", lambda **kwargs: created.append(kwargs))

    with pytest.raises(SystemExit) as exc_info:
        worker.run_simulator(config_path=str(config_path))

    assert exc_info.value.code == 1
    assert created == []


def test_run_simulator_boots_and_marks_success_without_contacting_ota(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    _write_config(tmp_path / "config.json")
    http = _RecordingHttp()
    monkeypatch.setattr(worker, "SimulatorHttpClient", lambda: http)

    worker.run_simulator(config_path="config.json", max_iterations=0)

    boot_state = json.loads((tmp_path / "boot_state.json").read_text())
    assert boot_state["boot_succeeded"] is True
    assert http.urls, "simulator should register with the API"
    assert not any(OTA_CHECK_PATH in url for url in http.urls)


# ---------------------------------------------------------------- config fallback


def test_resolve_config_path_keeps_existing_config(tmp_path):
    config_path = tmp_path / "config.json"
    _write_config(config_path)

    assert worker._resolve_config_path(str(config_path)) == str(config_path)


def test_resolve_config_path_falls_back_to_template_with_warning(tmp_path, caplog):
    missing = str(tmp_path / "missing.json")

    with caplog.at_level("WARNING", logger="simulator"):
        resolved = worker._resolve_config_path(missing)

    assert resolved == str(worker.TEMPLATE_CONFIG_PATH)
    assert any("falling back to the template" in r.getMessage() for r in caplog.records)


def test_resolve_config_path_exits_when_template_also_missing(tmp_path, monkeypatch):
    monkeypatch.setattr(worker, "TEMPLATE_CONFIG_PATH", tmp_path / "no-template.json")

    with pytest.raises(SystemExit) as exc_info:
        worker._resolve_config_path(str(tmp_path / "missing.json"))

    assert exc_info.value.code == 1


def test_template_config_is_loadable():
    from edge.shared.app.config import Config
    from edge.simulator.mocks import SimulatorFileSystem

    config = Config.load(SimulatorFileSystem(), path=str(worker.TEMPLATE_CONFIG_PATH))

    assert config.device_id == "simulator-device-1"


def test_main_runs_simulator_with_template_when_config_missing(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(worker, "run_simulator", lambda **kwargs: calls.append(kwargs))
    monkeypatch.setattr(sys, "argv", ["worker.py", "--config", str(tmp_path / "missing.json")])

    worker.main()

    [kwargs] = calls
    assert kwargs["config_path"] == str(worker.TEMPLATE_CONFIG_PATH)