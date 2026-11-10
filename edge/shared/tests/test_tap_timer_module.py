"""Tests for the tap timer device module in hardware/tap_timer/main.py."""

import calendar
import os
import sys
import types

import pytest

from edge.shared.app.module_runtime import ModuleRuntime


MODULE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "..", "hardware", "tap_timer", "main.py")
)
STATE_KEY = "_tap_timer_state"
HOUR = 3600
DRY = 0
SOAKED = 1023


def _load(variables=None):
    """Exec the module the same way ModuleRuntime does, including the variable preamble."""
    with open(MODULE_PATH, "r", encoding="utf-8") as handle:
        source = handle.read()
    scope = {}
    exec(ModuleRuntime._build_variable_preamble(variables or {}) + source, scope, scope)
    return scope


def _utc(year, month, day, hour=0, minute=0):
    return calendar.timegm((year, month, day, hour, minute, 0))


def _local_summer(day, hour, minute=0):
    """January 2027 local time (AEDT, UTC+11) as UTC seconds."""
    return _utc(2027, 1, day, hour, minute) - 11 * HOUR


@pytest.fixture(autouse=True)
def _clear_state():
    sys.modules.pop(STATE_KEY, None)
    yield
    sys.modules.pop(STATE_KEY, None)


def _new_state():
    return {"rain": [], "window_start": None, "window_decision": None}


def _evaluate(mod, state, now_s, wetness, threshold=100):
    return mod["_evaluate"](state, now_s, wetness, 17 * 60, 10, threshold)


def _feed_rain(mod, state, start_s, end_s, wetness, step_s=60):
    t = start_s
    while t < end_s:
        _evaluate(mod, state, t, wetness)
        t += step_s


# -- Variables -----------------------------------------------------------------

def test_defaults_when_no_variables_assigned():
    mod = _load()
    assert mod["VALVE_START_TIME"] == "17:00"
    assert mod["VALVE_RUN_DURATION_MINUTES"] == 10
    assert mod["RAIN_THRESHOLD_LAST_12H"] == 100
    assert mod["UTC_OFFSET_MINUTES"] == 600
    assert mod["USE_AU_DST"] is True


def test_assigned_variables_override_defaults():
    mod = _load({
        "VALVE_START_TIME": "06:30",
        "VALVE_RUN_DURATION_MINUTES": "25",
        "RAIN_THRESHOLD_LAST_12H": "300",
    })
    assert mod["VALVE_START_TIME"] == "06:30"
    assert mod["VALVE_RUN_DURATION_MINUTES"] == 25
    assert mod["RAIN_THRESHOLD_LAST_12H"] == 300


# -- Time helpers --------------------------------------------------------------

def test_parse_start_time():
    mod = _load()
    assert mod["_parse_start_time"]("17:00") == 17 * 60
    assert mod["_parse_start_time"](" 06:05 ") == 6 * 60 + 5
    for bad in ("1700", "24:00", "12:60", "ab:cd"):
        with pytest.raises(ValueError):
            mod["_parse_start_time"](bad)


def test_utc_offset_standard_and_daylight_time():
    mod = _load()
    offset = mod["_utc_offset_seconds"]
    assert offset(_utc(2027, 7, 1)) == 10 * HOUR
    assert offset(_utc(2027, 1, 15)) == 11 * HOUR


def test_utc_offset_dst_transitions():
    mod = _load()
    offset = mod["_utc_offset_seconds"]
    # 2026 DST starts Sun 4 Oct 02:00 AEST = Sat 3 Oct 16:00 UTC.
    assert offset(_utc(2026, 10, 3, 15, 59)) == 10 * HOUR
    assert offset(_utc(2026, 10, 3, 16, 0)) == 11 * HOUR
    # 2026 DST ends Sun 5 Apr 03:00 AEDT = Sat 4 Apr 16:00 UTC.
    assert offset(_utc(2026, 4, 4, 15, 59)) == 11 * HOUR
    assert offset(_utc(2026, 4, 4, 16, 0)) == 10 * HOUR


def test_utc_offset_without_dst():
    mod = _load({"USE_AU_DST": "false", "UTC_OFFSET_MINUTES": "330"})
    assert mod["_utc_offset_seconds"](_utc(2027, 1, 15)) == 330 * 60


def test_windows_use_local_time():
    mod = _load()
    start = _local_summer(15, 17)
    assert start == _utc(2027, 1, 15, 6)
    current, upcoming = mod["_windows"](start - 60, 17 * 60, 600)
    assert current is None
    assert upcoming == start
    current, upcoming = mod["_windows"](start + 300, 17 * 60, 600)
    assert current == start
    assert upcoming == start + 24 * HOUR
    current, upcoming = mod["_windows"](start + 600, 17 * 60, 600)
    assert current is None
    assert upcoming == start + 24 * HOUR


def test_iso_formatting():
    mod = _load()
    assert mod["_iso"](_utc(2027, 1, 15, 6, 5)) == "2027-01-15T06:05:00Z"
    assert mod["_iso"](None) is None


def test_wetness_scale():
    mod = _load()
    assert mod["_wetness"](65535) == 0
    assert mod["_wetness"](0) == 1023
    assert 500 <= mod["_wetness"](32768) <= 520


# -- Rain tracking -------------------------------------------------------------

def test_rain_buckets_keep_only_last_12_hours():
    mod = _load()
    buckets = []
    start = _utc(2027, 1, 15)
    t = start
    while t < start + 24 * HOUR:
        mod["_record_rain"](buckets, t, DRY)
        t += 60
    assert len(buckets) <= 12 * HOUR // mod["RAIN_BUCKET_SECONDS"] + 1


def test_rain_peak_slides_out_after_12_hours():
    mod = _load()
    state = _new_state()
    rain_at = _local_summer(15, 9)
    _evaluate(mod, state, rain_at, 400)
    result = _evaluate(mod, state, rain_at + 11 * HOUR, DRY)
    assert result["rain_peak_12h"] == 400
    assert result["rain_threshold_exceeded"] is True
    assert result["rain_clear_at"] == rain_at + 12 * HOUR
    result = _evaluate(mod, state, rain_at + 12 * HOUR + 60, DRY)
    assert result["rain_peak_12h"] == 0
    assert result["rain_threshold_exceeded"] is False
    assert result["rain_clear_at"] is None


# -- Valve and indicators ------------------------------------------------------

def test_valve_runs_for_window_when_dry():
    mod = _load()
    state = _new_state()
    start = _local_summer(15, 17)
    assert _evaluate(mod, state, start - 60, DRY)["valve_open"] is False
    result = _evaluate(mod, state, start, DRY)
    assert result["valve_open"] is True
    assert result["valve_not_run_today"] is False
    assert _evaluate(mod, state, start + 540, DRY)["valve_open"] is True
    assert _evaluate(mod, state, start + 600, DRY)["valve_open"] is False


def test_valve_skipped_when_rain_within_12_hours_of_window():
    mod = _load()
    state = _new_state()
    _feed_rain(mod, state, _local_summer(15, 10), _local_summer(15, 10, 30), 400)
    result = _evaluate(mod, state, _local_summer(15, 12), DRY)
    assert result["rain_threshold_exceeded"] is True
    assert result["valve_not_run_today"] is True
    result = _evaluate(mod, state, _local_summer(15, 17, 1), DRY)
    assert result["valve_open"] is False
    assert result["valve_not_run_today"] is True


def test_not_run_indicator_clears_after_skipped_window_passes():
    mod = _load()
    state = _new_state()
    _feed_rain(mod, state, _local_summer(15, 10), _local_summer(15, 10, 30), 400)
    _evaluate(mod, state, _local_summer(15, 17, 1), DRY)
    result = _evaluate(mod, state, _local_summer(15, 17, 15), DRY)
    assert result["valve_open"] is False
    assert result["rain_threshold_exceeded"] is True
    assert result["valve_not_run_today"] is False


def test_rain_that_clears_before_window_does_not_block():
    mod = _load()
    state = _new_state()
    _feed_rain(mod, state, _local_summer(15, 3), _local_summer(15, 4), 400)
    result = _evaluate(mod, state, _local_summer(15, 12), DRY)
    assert result["rain_threshold_exceeded"] is True
    assert result["valve_not_run_today"] is False
    result = _evaluate(mod, state, _local_summer(15, 17), DRY)
    assert result["rain_threshold_exceeded"] is False
    assert result["valve_open"] is True


def test_rain_below_threshold_does_not_block():
    mod = _load()
    state = _new_state()
    _evaluate(mod, state, _local_summer(15, 12), 100)
    result = _evaluate(mod, state, _local_summer(15, 17), DRY)
    assert result["rain_peak_12h"] == 100
    assert result["rain_threshold_exceeded"] is False
    assert result["valve_open"] is True


def test_rain_during_run_does_not_stop_valve():
    mod = _load()
    state = _new_state()
    start = _local_summer(15, 17)
    assert _evaluate(mod, state, start, DRY)["valve_open"] is True
    result = _evaluate(mod, state, start + 120, SOAKED)
    assert result["rain_threshold_exceeded"] is True
    assert result["valve_open"] is True
    assert result["valve_not_run_today"] is False


def test_skipped_window_stays_skipped_when_rain_clears_mid_window():
    mod = _load()
    state = _new_state()
    rain_at = _local_summer(15, 5, 2)
    _evaluate(mod, state, rain_at, 400)
    assert _evaluate(mod, state, _local_summer(15, 17), DRY)["valve_open"] is False
    result = _evaluate(mod, state, _local_summer(15, 17, 5), DRY)
    assert result["rain_threshold_exceeded"] is False
    assert result["valve_open"] is False


# -- run() ---------------------------------------------------------------------

class _FakePin:
    OUT = 1
    IN = 0
    PULL_UP = 2

    def __init__(self, machine, pin_id, mode=None, pull=None):
        self._machine = machine
        self.pin_id = pin_id

    def value(self, new_value=None):
        if new_value is None:
            return self._machine.input_values.get(self.pin_id, 1)
        self._machine.outputs[self.pin_id] = new_value
        return None


class _FakeAdc:
    def __init__(self, machine, pin):
        self._machine = machine
        self._pin_id = pin.pin_id

    def read_u16(self):
        return self._machine.adc_values[self._pin_id]


def _fake_machine(adc_values, input_values=None):
    machine = types.ModuleType("machine")
    machine.outputs = {}
    machine.adc_values = adc_values
    machine.input_values = input_values or {}

    class Pin(_FakePin):
        def __init__(self, pin_id, mode=None, pull=None):
            super().__init__(machine, pin_id, mode, pull)

    def adc(pin):
        return _FakeAdc(machine, pin)

    machine.Pin = Pin
    machine.ADC = adc
    return machine


@pytest.fixture
def rp2(monkeypatch):
    monkeypatch.setattr(sys, "platform", "rp2")

    def install(adc_values, input_values=None):
        machine = _fake_machine(adc_values, input_values)
        monkeypatch.setitem(sys.modules, "machine", machine)
        return machine

    return install


def test_run_rejects_other_platforms(monkeypatch):
    monkeypatch.setattr(sys, "platform", "linux")
    result = _load()["run"]({})
    assert result["success"] is False
    assert "not supported" in result["error"]


def test_run_opens_valve_and_reports_readings(rp2):
    machine = rp2({26: 32768, 27: 65535}, {1: 1})
    mod = _load()
    mod["_utc_now"] = lambda: _local_summer(15, 17, 2)
    result = mod["run"]({})
    assert result["success"] is True
    assert result["valve_open"] is True
    assert result["local_time"] == "17:02"
    assert result["current_window_start_utc"] == "2027-01-15T06:00:00Z"
    assert result["battery_voltage"] == pytest.approx(3.3, abs=0.01)
    assert result["rain_wetness"] == 0
    assert result["rain_digital_wet"] is False
    assert machine.outputs == {0: 1, 2: 0, 3: 0}


def test_run_keeps_rain_history_between_runs(rp2):
    machine = rp2({26: 40000, 27: 0}, {1: 0})
    mod = _load()
    mod["_utc_now"] = lambda: _local_summer(15, 12)
    result = mod["run"]({})
    assert result["rain_digital_wet"] is True
    assert result["rain_threshold_exceeded"] is True
    assert result["valve_not_run_today"] is True

    machine.adc_values[27] = 65535
    machine.input_values[1] = 1
    mod = _load()
    mod["_utc_now"] = lambda: _local_summer(15, 17, 1)
    result = mod["run"]({})
    assert result["rain_peak_12h"] == 1023
    assert result["valve_open"] is False
    assert machine.outputs == {0: 0, 2: 1, 3: 1}


def test_run_keeps_valve_closed_until_clock_synced(rp2):
    machine = rp2({26: 40000, 27: 65535})
    mod = _load()
    mod["_utc_now"] = lambda: None
    result = mod["run"]({})
    assert result["success"] is False
    assert result["valve_open"] is False
    assert machine.outputs[0] == 0


def test_run_closes_valve_on_error(rp2):
    machine = rp2({26: 40000, 27: 65535})
    mod = _load({"VALVE_START_TIME": "bad"})
    mod["_utc_now"] = lambda: _local_summer(15, 17, 1)
    machine.outputs[0] = 1
    result = mod["run"]({})
    assert result["success"] is False
    assert "VALVE_START_TIME" in result["error"]
    assert machine.outputs[0] == 0
