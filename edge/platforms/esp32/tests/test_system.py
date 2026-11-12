import pytest

from edge.platforms.esp32.hal import system as esp32_system
from edge.platforms.esp32.hal.system import MicroPythonSystem, lightsleep_known_broken
from edge.shared.hal.system import MicroPythonSystem as SharedMicroPythonSystem


def _caps(machine: str, version: str) -> dict[str, object]:
    return {"lightsleep": True, "deepsleep": True, "machine": machine, "runtime_version": version}


def test_lightsleep_broken_on_esp32c6_from_1_27_to_1_29():
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "1.27.0")) is True
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "1.28.0")) is True
    assert lightsleep_known_broken(_caps("ESP32-C6 module", "1.29.0")) is True
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "1.29.1")) is True


def test_lightsleep_not_broken_on_fixed_c6_versions():
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "1.30.0")) is False
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "1.30.0-preview")) is False
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "1.31.2")) is False
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "2.0.0")) is False


def test_lightsleep_not_broken_on_older_c6_or_other_chips():
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "1.26.1")) is False
    assert lightsleep_known_broken(_caps("Generic ESP32 module with ESP32", "1.28.0")) is False
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "")) is False
    assert lightsleep_known_broken({}) is False


def _patch_shared(monkeypatch: pytest.MonkeyPatch, caps: dict[str, object], light_sleep_calls: list[int]) -> None:
    def get_sleep_capabilities(self: SharedMicroPythonSystem) -> dict[str, object]:
        return dict(caps)

    def light_sleep_ms(self: SharedMicroPythonSystem, ms: int) -> bool:
        light_sleep_calls.append(ms)
        return True

    monkeypatch.setattr(SharedMicroPythonSystem, "get_sleep_capabilities", get_sleep_capabilities)
    monkeypatch.setattr(SharedMicroPythonSystem, "light_sleep_ms", light_sleep_ms)


def test_capabilities_hide_lightsleep_on_affected_c6(monkeypatch: pytest.MonkeyPatch) -> None:
    _patch_shared(monkeypatch, _caps("ESP32C6 module with ESP32C6", "1.28.0"), [])

    caps = MicroPythonSystem().get_sleep_capabilities()

    assert caps["lightsleep"] is False
    assert caps["lightsleep_disabled"] == "micropython#19396"


def test_light_sleep_falls_back_to_regular_sleep_on_affected_c6(monkeypatch: pytest.MonkeyPatch) -> None:
    light_sleep_calls: list[int] = []
    _patch_shared(monkeypatch, _caps("ESP32C6 module with ESP32C6", "1.28.0"), light_sleep_calls)
    system = MicroPythonSystem()
    sleeps: list[int] = []

    def sleep_ms(ms: int) -> None:
        sleeps.append(ms)

    monkeypatch.setattr(system, "sleep_ms", sleep_ms)

    assert system.light_sleep_ms(15000) is False
    assert sleeps == [15000]
    assert light_sleep_calls == []


def test_light_sleep_used_on_fixed_c6(monkeypatch: pytest.MonkeyPatch) -> None:
    light_sleep_calls: list[int] = []
    _patch_shared(monkeypatch, _caps("ESP32C6 module with ESP32C6", "1.30.0"), light_sleep_calls)
    system = MicroPythonSystem()

    assert system.light_sleep_ms(15000) is True
    assert light_sleep_calls == [15000]
    caps = system.get_sleep_capabilities()
    assert caps["lightsleep"] is True
    assert "lightsleep_disabled" not in caps


def test_light_sleep_used_on_unaffected_chip(monkeypatch: pytest.MonkeyPatch) -> None:
    light_sleep_calls: list[int] = []
    _patch_shared(monkeypatch, _caps("Generic ESP32 module with ESP32", "1.28.0"), light_sleep_calls)
    system = MicroPythonSystem()

    assert system.light_sleep_ms(15000) is True
    assert light_sleep_calls == [15000]
    assert system.get_sleep_capabilities()["lightsleep"] is True


def test_module_exports_platform_system():
    assert esp32_system.__all__ == ["MicroPythonSystem"]
