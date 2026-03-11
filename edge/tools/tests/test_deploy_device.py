import types
from pathlib import Path

import pytest

import edge.tools.deploy_device as deploy_device


def test_validate_logging_payload_accepts_defaults():
    deploy_device._validate_logging_payload({"enabled_uplink": True, "buffer_max_bytes": 4096, "flush_interval_ms": 30000})


def test_validate_logging_payload_rejects_small_buffer():
    with pytest.raises(deploy_device.DeployError):
        deploy_device._validate_logging_payload({"buffer_max_bytes": 256})


def test_load_and_validate_config_rejects_placeholder_plaintext_values(tmp_path):
    config_path = tmp_path / "config.json"
    config_path.write_text(
        '{"device_id":"esp32-001","api_url":"http://localhost:8000","api_key":"replace-with-device-api-key","wifi_ssid":"replace-with-ssid","wifi_password":"replace-with-password","heartbeat_interval_ms":30000,"max_boot_attempts":3}',
        encoding="utf-8",
    )

    with pytest.raises(deploy_device.DeployError):
        deploy_device._load_and_validate_config(config_path)


def test_verify_remote_imports_checks_shared_control_modules(monkeypatch):
    calls = []

    def fake_run_mpremote(port: str, args, phase: str):
        calls.append((port, list(args), phase))
        return types.SimpleNamespace(returncode=0, stdout="IMPORTS_OK\n")

    monkeypatch.setattr(deploy_device, "_run_mpremote", fake_run_mpremote)

    deploy_device._verify_remote_imports("COM5", "esp32")

    assert calls[0][2] == "remote import verification"
    assert "import edge.shared.app.control_loop" in calls[0][1][1]
    assert "import edge.shared.app.module_runtime" in calls[0][1][1]


def test_maybe_copy_config_backs_up_existing_config(monkeypatch):
    calls = []

    def fake_device_has_config(port: str) -> bool:
        return True

    def fake_run_mpremote(port: str, args, phase: str):
        calls.append((port, list(args), phase))
        return types.SimpleNamespace(returncode=0, stdout="")

    def fake_mark_pending_config_update(port: str, config_version: str):
        calls.append((port, [config_version], "mark pending config update"))

    monkeypatch.setattr(deploy_device, "_device_has_config", fake_device_has_config)
    monkeypatch.setattr(deploy_device, "_run_mpremote", fake_run_mpremote)
    monkeypatch.setattr(deploy_device, "_mark_pending_config_update", fake_mark_pending_config_update)

    config_path = Path("config.json")
    config_path.write_text('{"current_version":"1.2.0"}', encoding="utf-8")

    result = deploy_device._maybe_copy_config("COM3", config_path, True, True)

    config_path.unlink()

    assert result == "overwritten"
    assert calls[0][1] == ["cp", ":/config.json", ":/config_prev.json"]
    assert calls[1][1] == ["cp", "config.json", ":/config.json"]
    assert calls[2] == ("COM3", ["1.2.0"], "mark pending config update")


def test_maybe_copy_config_creates_without_backup_when_missing(monkeypatch):
    calls = []

    def fake_device_has_config(port: str) -> bool:
        return False

    def fake_run_mpremote(port: str, args, phase: str):
        calls.append((port, list(args), phase))
        return types.SimpleNamespace(returncode=0, stdout="")

    monkeypatch.setattr(deploy_device, "_device_has_config", fake_device_has_config)
    monkeypatch.setattr(deploy_device, "_run_mpremote", fake_run_mpremote)

    config_path = Path("config.json")
    config_path.write_text('{"current_version":"1.2.0"}', encoding="utf-8")

    result = deploy_device._maybe_copy_config("COM3", config_path, False, True)

    config_path.unlink()

    assert result == "created"
    assert calls == [("COM3", ["cp", "config.json", ":/config.json"], "copy config.json")]


def test_mark_pending_config_update_writes_expected_flags(monkeypatch):
    calls = []

    def fake_run_mpremote(port: str, args, phase: str):
        calls.append((port, list(args), phase))
        return types.SimpleNamespace(returncode=0, stdout="BOOT_STATE_UPDATED\n")

    monkeypatch.setattr(deploy_device, "_run_mpremote", fake_run_mpremote)

    deploy_device._mark_pending_config_update("COM4", "1.3.0")

    assert calls[0][2] == "mark pending config update"
    assert calls[0][1][0] == "exec"
    assert "pending_app_changed'" in calls[0][1][1]
    assert "pending_config_changed'" in calls[0][1][1]
    assert "1.3.0" in calls[0][1][1]
