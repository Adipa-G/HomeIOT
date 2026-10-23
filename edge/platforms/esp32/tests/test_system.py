from edge.platforms.esp32.hal import system as esp32_system
from edge.platforms.esp32.hal.system import MicroPythonSystem, lightsleep_known_broken
from edge.shared.hal.system import MicroPythonSystem as SharedMicroPythonSystem


def _caps(machine, version):
    return {"lightsleep": True, "deepsleep": True, "machine": machine, "runtime_version": version}


def test_lightsleep_broken_on_esp32c6_from_1_27():
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "1.27.0")) is True
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "1.28.0")) is True
    assert lightsleep_known_broken(_caps("ESP32-C6 module", "1.29.0")) is True


def test_lightsleep_not_broken_on_older_c6_or_other_chips():
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "1.26.1")) is False
    assert lightsleep_known_broken(_caps("Generic ESP32 module with ESP32", "1.28.0")) is False
    assert lightsleep_known_broken(_caps("ESP32C6 module with ESP32C6", "")) is False
    assert lightsleep_known_broken({}) is False


def _patch_shared(monkeypatch, caps, light_sleep_calls):
    monkeypatch.setattr(SharedMicroPythonSystem, "get_sleep_capabilities", lambda self: dict(caps))
    monkeypatch.setattr(
        SharedMicroPythonSystem,
        "light_sleep_ms",
        lambda self, ms: light_sleep_calls.append(ms) or True,
    )


def test_capabilities_hide_lightsleep_on_affected_c6(monkeypatch):
    _patch_shared(monkeypatch, _caps("ESP32C6 module with ESP32C6", "1.28.0"), [])

    caps = MicroPythonSystem().get_sleep_capabilities()

    assert caps["lightsleep"] is False
    assert caps["lightsleep_disabled"] == "micropython#19396"


def test_light_sleep_falls_back_to_regular_sleep_on_affected_c6(monkeypatch):
    light_sleep_calls = []
    _patch_shared(monkeypatch, _caps("ESP32C6 module with ESP32C6", "1.28.0"), light_sleep_calls)
    system = MicroPythonSystem()
    sleeps = []
    monkeypatch.setattr(system, "sleep_ms", lambda ms: sleeps.append(ms))

    assert system.light_sleep_ms(15000) is False
    assert sleeps == [15000]
    assert light_sleep_calls == []


def test_light_sleep_used_on_unaffected_chip(monkeypatch):
    light_sleep_calls = []
    _patch_shared(monkeypatch, _caps("Generic ESP32 module with ESP32", "1.28.0"), light_sleep_calls)
    system = MicroPythonSystem()

    assert system.light_sleep_ms(15000) is True
    assert light_sleep_calls == [15000]
    assert system.get_sleep_capabilities()["lightsleep"] is True


def test_module_exports_platform_system():
    assert esp32_system.__all__ == ["MicroPythonSystem"]
