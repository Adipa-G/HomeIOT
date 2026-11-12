"""Tests for the tap timer device module in hardware/tap_timer/main.py."""

import calendar
import os
import sys
import time
import types
from typing import Any

import pytest

from edge.shared.app.module_runtime import ModuleRuntime


MODULE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "hardware", "tap_timer", "main.py")
)
VALVE, DIGITAL, RAIN_LED, NOT_RUN_LED, SENSOR_POWER = 0, 1, 2, 3, 4
BATTERY_ADC, RAIN_ADC = 26, 27
DRY_RAW, WET_RAW = 65535, 0


class _FakeMachine(types.ModuleType):
    def __init__(self):
        super().__init__("machine")
        self.outputs: dict[int, int] = {}
        self.adc_values: dict[int, int] = {BATTERY_ADC: 32768, RAIN_ADC: DRY_RAW}
        self.input_values: dict[int, int] = {DIGITAL: 1}
        self.sensor_power_during_reads: list[int | None] = []
        machine = self

        class Pin:
            OUT = 1
            IN = 0
            PULL_UP = 2

            def __init__(self, pin_id: int, mode: int | None = None, pull: int | None = None):
                self.pin_id = pin_id
                self.mode = mode

            def value(self, new_value: int | None = None) -> int | None:
                if new_value is not None:
                    machine.outputs[self.pin_id] = new_value
                    return None
                if self.mode == Pin.OUT:
                    return machine.outputs.get(self.pin_id, 0)
                machine.sensor_power_during_reads.append(machine.outputs.get(SENSOR_POWER))
                return machine.input_values[self.pin_id]

        class ADC:
            def __init__(self, pin_id: int):
                self.pin_id = pin_id

            def read_u16(self) -> int:
                if self.pin_id == RAIN_ADC:
                    machine.sensor_power_during_reads.append(machine.outputs.get(SENSOR_POWER))
                return machine.adc_values[self.pin_id]

        self.Pin = Pin
        self.ADC = ADC


@pytest.fixture
def machine(monkeypatch: pytest.MonkeyPatch) -> _FakeMachine:
    fake = _FakeMachine()
    monkeypatch.setattr(sys, "platform", "rp2")
    monkeypatch.setitem(sys.modules, "machine", fake)
    return fake


def _local(hour: int, minute: int = 0, day: int = 15) -> int:
    """Local AEST (UTC+10) wall time as Unix seconds."""
    return calendar.timegm((2027, 1, day, hour, minute, 0)) - 10 * 3600


def _run(local_s: float, variables: dict[str, Any] | None = None) -> Any:
    with open(MODULE_PATH, "r", encoding="utf-8") as handle:
        source = handle.read()
    scope: dict[str, Any] = {}
    exec(ModuleRuntime._build_variable_preamble(variables or {}) + source, scope, scope)

    def no_sleep(_s: float) -> None:
        pass

    scope["time"] = types.SimpleNamespace(time=lambda: local_s, gmtime=time.gmtime, sleep=no_sleep)
    return scope["run"]({})


def test_defaults_and_overrides():
    with open(MODULE_PATH, "r", encoding="utf-8") as handle:
        source = handle.read()
    scope: dict[str, Any] = {}
    exec(source, scope, scope)
    assert (scope["VALVE_START_TIME"], scope["VALVE_RUN_DURATION_MINUTES"]) == ("17:00", 10)
    assert (scope["RAIN_THRESHOLD"], scope["TURN_VALVE_ON_MANUALLY"]) == (100, False)

    scope: dict[str, Any] = {}
    exec(ModuleRuntime._build_variable_preamble({
        "VALVE_START_TIME": "06:30", "VALVE_RUN_DURATION_MINUTES": "25",
        "RAIN_THRESHOLD": "300", "TURN_VALVE_ON_MANUALLY": "True",
    }) + source, scope, scope)
    assert (scope["VALVE_START_TIME"], scope["VALVE_RUN_DURATION_MINUTES"]) == ("06:30", 25)
    assert (scope["RAIN_THRESHOLD"], scope["TURN_VALVE_ON_MANUALLY"]) == (300, True)


def test_module_source_stays_small():
    # The Pico W ran out of heap compiling an 11 KB version of this module.
    assert os.path.getsize(MODULE_PATH) < 5000


def test_rejects_other_platforms(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(sys, "platform", "linux")
    result = _run(_local(17))
    assert result["success"] is False
    assert "not supported" in result["error"]


def test_valve_open_only_during_window_when_dry(machine: _FakeMachine):
    assert _run(_local(16, 59))["valve_open"] == 0
    result = _run(_local(17, 0))
    assert result["success"] is True
    assert result["valve_open"] == 1
    assert type(result["valve_open"]) is int
    assert type(result["manual_override"]) is int
    assert result["local_time"] == "17:00"
    assert _run(_local(17, 9))["valve_open"] == 1
    assert _run(_local(17, 10))["valve_open"] == 0
    assert machine.outputs[VALVE] == 0


def test_reports_readings(machine: _FakeMachine):
    machine.adc_values[RAIN_ADC] = 32768
    machine.input_values[DIGITAL] = 0
    result = _run(_local(12))
    assert abs(result["battery_voltage"] - 3.3) <= 0.01
    assert 500 <= result["rain_wetness"] <= 520
    assert result["rain_digital_wet"] is True
    assert result["rain_threshold_exceeded"] is True
    assert machine.outputs[RAIN_LED] == 1


def test_rain_sensor_powered_only_while_reading(machine: _FakeMachine):
    _run(_local(12))
    assert machine.sensor_power_during_reads == [1, 1]
    assert machine.outputs[SENSOR_POWER] == 0


def test_rain_at_start_skips_window_and_flags_until_midnight(machine: _FakeMachine):
    machine.adc_values[RAIN_ADC] = WET_RAW
    result = _run(_local(17, 0))
    assert result["valve_open"] == 0
    assert result["valve_not_run_today"] is True

    machine.adc_values[RAIN_ADC] = DRY_RAW
    assert _run(_local(17, 5))["valve_open"] == 1
    assert _run(_local(17, 5))["valve_not_run_today"] is False

    machine.outputs[VALVE] = 0
    machine.outputs[NOT_RUN_LED] = 1
    assert _run(_local(23, 59))["valve_not_run_today"] is True
    assert machine.outputs[NOT_RUN_LED] == 1
    assert _run(_local(0, 0, day=16))["valve_not_run_today"] is False
    assert machine.outputs[NOT_RUN_LED] == 0


def test_skipped_window_stays_flagged_after_window(machine: _FakeMachine):
    machine.adc_values[RAIN_ADC] = WET_RAW
    _run(_local(17, 9))
    machine.adc_values[RAIN_ADC] = DRY_RAW
    result = _run(_local(18))
    assert result["valve_open"] == 0
    assert result["valve_not_run_today"] is True
    assert result["rain_threshold_exceeded"] is False


def test_rain_during_run_keeps_valve_open(machine: _FakeMachine):
    assert _run(_local(17, 0))["valve_open"] == 1
    machine.adc_values[RAIN_ADC] = WET_RAW
    result = _run(_local(17, 5))
    assert result["rain_threshold_exceeded"] is True
    assert result["valve_open"] == 1
    assert result["valve_not_run_today"] is False


def test_threshold_override(machine: _FakeMachine):
    machine.adc_values[RAIN_ADC] = 32768
    assert _run(_local(17), {"RAIN_THRESHOLD": "600"})["valve_open"] == 1


def test_window_crossing_midnight(machine: _FakeMachine):
    variables = {"VALVE_START_TIME": "23:55"}
    assert _run(_local(23, 58), variables)["valve_open"] == 1
    assert _run(_local(0, 4, day=16), variables)["valve_open"] == 1
    assert _run(_local(0, 5, day=16), variables)["valve_open"] == 0


def test_manual_override(machine: _FakeMachine):
    machine.adc_values[RAIN_ADC] = WET_RAW
    result = _run(_local(12), {"TURN_VALVE_ON_MANUALLY": "True"})
    assert result["valve_open"] == 1
    assert result["manual_override"] == 1
    assert machine.outputs[VALVE] == 1

    result = _run(_local(12, 1), {"TURN_VALVE_ON_MANUALLY": "False"})
    assert result["valve_open"] == 0
    assert machine.outputs[VALVE] == 0


def test_clock_not_synced_keeps_valve_closed_unless_manual(machine: _FakeMachine):
    unsynced = calendar.timegm((2021, 1, 1, 7, 0, 0))
    result = _run(unsynced)
    assert result["valve_open"] == 0
    assert result["local_time"] is None
    assert _run(unsynced, {"TURN_VALVE_ON_MANUALLY": "True"})["valve_open"] == 1


def test_error_closes_valve_and_powers_off_sensor(machine: _FakeMachine):
    machine.outputs[VALVE] = 1
    result = _run(_local(17), {"VALVE_START_TIME": "bad"})
    assert result["success"] is False
    assert machine.outputs[VALVE] == 0
    assert machine.outputs[SENSOR_POWER] == 0