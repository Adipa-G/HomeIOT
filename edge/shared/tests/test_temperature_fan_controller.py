import importlib.util
import os
import sys
import types
from collections.abc import Callable
from typing import Any

import pytest

from edge.shared.tests.mocks.fake_module import fake_module


MODULE_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        "..", "..", "..",
        "hardware", "tempreature_fan_controller", "main.py",
    )
)


def _load_module() -> Any:
    spec = importlib.util.spec_from_file_location("temperature_fan_controller_main", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _duty(percent: float) -> int:
    return int((percent / 100) * 65535)


class FakeHardware:
    """Simulates the RP2 peripherals used by the fan controller."""

    def __init__(
        self,
        temperature: float = 30.0,
        roms: list[bytes] | None = None,
        tach_pulses: list[int] | None = None,
        read_temp_error: Exception | None = None,
    ):
        self.temperature = temperature
        self.roms = [b"rom-1"] if roms is None else roms
        # Pulses delivered to the tach IRQ during each 1 s RPM measurement window.
        self.tach_pulses = list(tach_pulses or [])
        self.read_temp_error = read_temp_error
        self.tach_handler: Callable[[object], None] | None = None
        self.irq_trigger: object = None
        self.pwm_freq: int | None = None
        self.duties: list[int] = []
        self.sleeps: list[float] = []
        self.pin_args: list[tuple[object, tuple[object, ...]]] = []
        self.converted = False

    def build_modules(self) -> dict[str, Any]:
        hw = self

        class Pin:
            IN = "IN"
            PULL_UP = "PULL_UP"
            IRQ_FALLING = "IRQ_FALLING"

            def __init__(self, pin_id: object, *args: object):
                self.pin_id = pin_id
                hw.pin_args.append((pin_id, args))

            def irq(self, trigger: object, handler: Callable[[object], None]) -> None:
                hw.irq_trigger = trigger
                hw.tach_handler = handler

        class PWM:
            def __init__(self, pin: object):
                self.pin = pin

            def freq(self, value: int) -> None:
                hw.pwm_freq = value

            def duty_u16(self, value: int) -> None:
                hw.duties.append(value)

        class OneWire:
            def __init__(self, pin: object):
                self.pin = pin

        class DS18X20:
            def __init__(self, bus: object):
                self.bus = bus

            def scan(self) -> list[bytes]:
                return hw.roms

            def convert_temp(self) -> None:
                hw.converted = True

            def read_temp(self, rom: bytes) -> float:
                if hw.read_temp_error is not None:
                    raise hw.read_temp_error
                return hw.temperature

        machine = fake_module("machine")
        machine.Pin = Pin
        machine.PWM = PWM
        onewire = fake_module("onewire")
        onewire.OneWire = OneWire
        ds18x20 = fake_module("ds18x20")
        ds18x20.DS18X20 = DS18X20
        return {"machine": machine, "onewire": onewire, "ds18x20": ds18x20}

    def sleep(self, seconds: float) -> None:
        self.sleeps.append(seconds)
        if seconds == 1.0 and self.tach_handler is not None:
            pulses = self.tach_pulses.pop(0) if self.tach_pulses else 0
            for _ in range(pulses):
                self.tach_handler(None)


@pytest.fixture
def run_controller(monkeypatch: pytest.MonkeyPatch) -> Callable[..., Any]:
    def _run(hw: FakeHardware, platform: str = "rp2") -> Any:
        module = _load_module()
        for name, fake in hw.build_modules().items():
            monkeypatch.setitem(sys.modules, name, fake)
        monkeypatch.setattr(module, "sys", types.SimpleNamespace(platform=platform))
        monkeypatch.setattr(module, "time", types.SimpleNamespace(sleep=hw.sleep))
        return module.run({})

    return _run


def test_returns_error_on_unsupported_platform(run_controller: Callable[..., Any]):
    hw = FakeHardware()

    result = run_controller(hw, platform="linux")

    assert result == {
        "success": False,
        "platform": "linux",
        "error": "Module not supported on platform: linux",
    }
    assert hw.duties == []


def test_returns_error_when_no_sensor_found(run_controller: Callable[..., Any]):
    hw = FakeHardware(roms=[])

    result = run_controller(hw)

    assert result == {
        "success": False,
        "platform": "rp2",
        "error": "No DS18X20 sensors found.",
    }
    assert hw.duties == []


@pytest.mark.parametrize(
    "temperature, expected_speed",
    [
        (20.0, 0),
        (34.9, 0),
        (35.0, 25),
        (39.9, 25),
        (40.0, 50),
        (44.9, 50),
        (45.0, 100),
        (70.0, 100),
    ],
)
def test_maps_temperature_to_fan_speed(run_controller: Callable[..., Any], temperature: float, expected_speed: int):
    hw = FakeHardware(temperature=temperature, tach_pulses=[40])

    result = run_controller(hw)

    assert result["success"] is True
    assert result["temperature"] == temperature
    assert result["target_speed"] == expected_speed
    assert hw.duties == [_duty(expected_speed)]


def test_reports_rpm_from_tach_pulses(run_controller: Callable[..., Any]):
    # 2 pulses per revolution over a 1 s window: 50 pulses -> 25 rev/s -> 1500 RPM.
    hw = FakeHardware(temperature=42.0, tach_pulses=[50])

    result = run_controller(hw)

    assert result == {
        "success": True,
        "platform": "rp2",
        "temperature": 42.0,
        "target_speed": 50,
        "rpm": 1500,
    }
    assert isinstance(result["rpm"], int)


def test_configures_peripherals(run_controller: Callable[..., Any]):
    hw = FakeHardware(temperature=30.0)

    run_controller(hw)

    assert hw.converted is True
    assert hw.pwm_freq == 25000
    assert hw.irq_trigger == "IRQ_FALLING"
    assert (2, ("IN", "PULL_UP")) in hw.pin_args


def test_kick_starts_stalled_fan_at_low_speed(run_controller: Callable[..., Any]):
    hw = FakeHardware(temperature=36.0, tach_pulses=[0, 20])

    result = run_controller(hw)

    assert result["success"] is True
    assert result["target_speed"] == 25
    assert result["rpm"] == 600
    assert hw.duties == [_duty(25), _duty(50), _duty(25)]
    assert hw.sleeps == [1.0, 0.4, 1.0]


def test_does_not_kick_start_when_fan_is_spinning(run_controller: Callable[..., Any]):
    hw = FakeHardware(temperature=36.0, tach_pulses=[10])

    result = run_controller(hw)

    assert result["rpm"] == 300
    assert hw.duties == [_duty(25)]
    assert hw.sleeps == [1.0]


@pytest.mark.parametrize("temperature, expected_speed", [(30.0, 0), (42.0, 50), (50.0, 100)])
def test_does_not_kick_start_outside_low_speed_range(run_controller: Callable[..., Any], temperature: float, expected_speed: int):
    hw = FakeHardware(temperature=temperature, tach_pulses=[0])

    result = run_controller(hw)

    assert result["rpm"] == 0
    assert hw.duties == [_duty(expected_speed)]
    assert hw.sleeps == [1.0]


def test_returns_error_when_hardware_raises(run_controller: Callable[..., Any]):
    hw = FakeHardware(read_temp_error=OSError("CRC error"))

    result = run_controller(hw)

    assert result == {
        "success": False,
        "platform": "rp2",
        "error": "CRC error",
    }
