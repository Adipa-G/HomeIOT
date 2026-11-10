import sys
import time

# --- PIN CONFIGURATION ---
VOLTAGE_SENSOR_PIN = 26
RAIN_SENSOR_ACTIVATION_PIN = 4
RAIN_ANALOG_SENSOR_PIN = 27
RAIN_DIGITAL_SENSOR_PIN = 1
VALVE_CONTROL_PIN = 0
RAIN_THRESHOLD_EXCEEDED_INDICATOR_PIN = 2
VALVE_NOT_RUN_TODAY_INDICATOR_PIN = 3

# --- OVERRIDABLE SETTINGS ---
# Module variables are injected before this source runs, so only fall back to
# the defaults when the variable hasn't been configured.
try:
    VALVE_START_TIME
except NameError:
    VALVE_START_TIME = "17:00"
try:
    VALVE_RUN_DURATION_MINUTES
except NameError:
    VALVE_RUN_DURATION_MINUTES = 10
try:
    RAIN_THRESHOLD_LAST_12H
except NameError:
    RAIN_THRESHOLD_LAST_12H = 100
try:
    UTC_OFFSET_MINUTES
except NameError:
    UTC_OFFSET_MINUTES = 600
try:
    USE_AU_DST
except NameError:
    USE_AU_DST = True
try:
    TURN_VALVE_ON_MANUALLY
except NameError:
    TURN_VALVE_ON_MANUALLY = False

# --- CONSTANTS ---
VSYS_DIVIDER_RATIO = 2.0
ADC_REFERENCE_VOLTAGE = 3.3
WETNESS_SCALE_MAX = 1023
RAIN_WINDOW_SECONDS = 12 * 3600
RAIN_BUCKET_SECONDS = 600
RAIN_SENSOR_SETTLE_SECONDS = 0.1
MIN_SYNCED_YEAR = 2024

# Modules are re-executed on every run, so in-memory state lives in sys.modules
# to survive between runs. A reboot clears it.
_STATE_KEY = "_tap_timer_state"


def _get_state():
    state = sys.modules.get(_STATE_KEY)
    if not isinstance(state, dict):
        state = {"rain": [], "window_start": None, "window_decision": None}
        sys.modules[_STATE_KEY] = state
    return state


def _days_from_civil(year, month, day):
    if month <= 2:
        year -= 1
    era = (year if year >= 0 else year - 399) // 400
    year_of_era = year - era * 400
    day_of_year = (153 * (month + (-3 if month > 2 else 9)) + 2) // 5 + day - 1
    day_of_era = year_of_era * 365 + year_of_era // 4 - year_of_era // 100 + day_of_year
    return era * 146097 + day_of_era - 719468


def _civil_from_days(days):
    days += 719468
    era = (days if days >= 0 else days - 146096) // 146097
    day_of_era = days - era * 146097
    year_of_era = (day_of_era - day_of_era // 1460 + day_of_era // 36524 - day_of_era // 146096) // 365
    year = year_of_era + era * 400
    day_of_year = day_of_era - (365 * year_of_era + year_of_era // 4 - year_of_era // 100)
    shifted_month = (5 * day_of_year + 2) // 153
    day = day_of_year - (153 * shifted_month + 2) // 5 + 1
    month = shifted_month + (3 if shifted_month < 10 else -9)
    if month <= 2:
        year += 1
    return year, month, day


def _iso(seconds):
    if seconds is None:
        return None
    seconds = int(seconds)
    days = seconds // 86400
    remainder = seconds - days * 86400
    year, month, day = _civil_from_days(days)
    return "%04d-%02d-%02dT%02d:%02d:%02dZ" % (
        year, month, day, remainder // 3600, (remainder % 3600) // 60, remainder % 60,
    )


def _utc_now():
    """Unix seconds from the RTC, or None if the clock hasn't been synced yet."""
    parts = time.gmtime()
    if parts[0] < MIN_SYNCED_YEAR:
        return None
    return _days_from_civil(parts[0], parts[1], parts[2]) * 86400 + parts[3] * 3600 + parts[4] * 60 + parts[5]


def _first_sunday(year, month):
    weekday = (_days_from_civil(year, month, 1) + 3) % 7  # Monday is 0
    return 1 + (6 - weekday) % 7


def _utc_offset_seconds(utc_seconds):
    base = int(UTC_OFFSET_MINUTES) * 60
    if not USE_AU_DST:
        return base
    year = _civil_from_days(utc_seconds // 86400)[0]
    # Australian DST: from 02:00 standard time on the first Sunday in October
    # until 03:00 daylight time on the first Sunday in April.
    dst_start = _days_from_civil(year, 10, _first_sunday(year, 10)) * 86400 + 2 * 3600 - base
    dst_end = _days_from_civil(year, 4, _first_sunday(year, 4)) * 86400 + 3 * 3600 - (base + 3600)
    if utc_seconds >= dst_start or utc_seconds < dst_end:
        return base + 3600
    return base


def _parse_start_time(value):
    parts = str(value).strip().split(":")
    if len(parts) != 2:
        raise ValueError("VALVE_START_TIME must be HH:MM, got: {}".format(value))
    hour = int(parts[0])
    minute = int(parts[1])
    if not (0 <= hour < 24 and 0 <= minute < 60):
        raise ValueError("VALVE_START_TIME out of range: {}".format(value))
    return hour * 60 + minute


def _windows(now_s, start_minutes, duration_s):
    """Return (current_window_start, next_window_start) in UTC seconds."""
    local_now = now_s + _utc_offset_seconds(now_s)
    local_midnight = local_now - local_now % 86400
    current = None
    upcoming = None
    for day in (-1, 0, 1, 2):
        local_start = local_midnight + day * 86400 + start_minutes * 60
        guess_utc = local_start - _utc_offset_seconds(now_s)
        start_utc = local_start - _utc_offset_seconds(guess_utc)
        if start_utc <= now_s < start_utc + duration_s:
            current = start_utc
        elif start_utc > now_s and upcoming is None:
            upcoming = start_utc
    return current, upcoming


def _wetness(raw_u16):
    """Rain sensor output drops as it gets wetter; map to 0 (dry) .. 1023 (soaked)."""
    raw_u16 = max(0, min(65535, int(raw_u16)))
    return (65535 - raw_u16) * WETNESS_SCALE_MAX // 65535


def _record_rain(buckets, now_s, wetness):
    key = now_s // RAIN_BUCKET_SECONDS
    if buckets and buckets[-1][0] == key:
        bucket = buckets[-1]
        bucket[1] = now_s
        if wetness > bucket[2]:
            bucket[2] = wetness
    else:
        buckets.append([key, now_s, wetness])
    cutoff = now_s - RAIN_WINDOW_SECONDS
    while buckets and buckets[0][1] <= cutoff:
        buckets.pop(0)


def _rain_peak(buckets):
    peak = 0
    for bucket in buckets:
        if bucket[2] > peak:
            peak = bucket[2]
    return peak


def _rain_clear_at(buckets, threshold):
    """When the 12h peak drops back to the threshold, assuming no more rain."""
    last_wet = None
    for bucket in buckets:
        if bucket[2] > threshold and (last_wet is None or bucket[1] > last_wet):
            last_wet = bucket[1]
    if last_wet is None:
        return None
    return last_wet + RAIN_WINDOW_SECONDS


def _evaluate(state, now_s, wetness, start_minutes, duration_minutes, threshold):
    buckets = state["rain"]
    _record_rain(buckets, now_s, wetness)
    peak = _rain_peak(buckets)
    rain_exceeded = peak > threshold
    clear_at = _rain_clear_at(buckets, threshold)

    duration_s = max(0, min(1439 * 60, int(duration_minutes * 60)))
    current, upcoming = _windows(now_s, start_minutes, duration_s)

    if current is not None:
        # Decide once per window; rain arriving mid-run doesn't stop the valve.
        if state["window_start"] != current:
            state["window_start"] = current
            state["window_decision"] = "skip" if rain_exceeded else "run"
        valve_open = state["window_decision"] == "run"
        not_run_today = not valve_open
    else:
        valve_open = False
        not_run_today = clear_at is not None and upcoming is not None and clear_at > upcoming

    return {
        "valve_open": valve_open,
        "rain_peak_12h": peak,
        "rain_threshold_exceeded": rain_exceeded,
        "rain_clear_at": clear_at,
        "valve_not_run_today": not_run_today,
        "current_window_start": current,
        "next_window_start": upcoming,
    }


def _read_rain_sensor(machine):
    """Power the sensor only while reading so the probe doesn't corrode.

    Returns (raw_u16, digital_wet). The digital output is pulled low while wet.
    """
    power = machine.Pin(RAIN_SENSOR_ACTIVATION_PIN, machine.Pin.OUT)
    power.value(1)
    try:
        time.sleep(RAIN_SENSOR_SETTLE_SECONDS)
        raw = machine.ADC(machine.Pin(RAIN_ANALOG_SENSOR_PIN)).read_u16()
        digital = machine.Pin(RAIN_DIGITAL_SENSOR_PIN, machine.Pin.IN, machine.Pin.PULL_UP)
        return raw, digital.value() == 0
    finally:
        power.value(0)


def run(ctx):
    platform = sys.platform
    if platform != "rp2":
        return {
            "success": False,
            "platform": platform,
            "error": "Module not supported on platform: {}".format(platform),
        }

    valve = None
    try:
        import machine

        valve = machine.Pin(VALVE_CONTROL_PIN, machine.Pin.OUT)
        rain_indicator = machine.Pin(RAIN_THRESHOLD_EXCEEDED_INDICATOR_PIN, machine.Pin.OUT)
        not_run_indicator = machine.Pin(VALVE_NOT_RUN_TODAY_INDICATOR_PIN, machine.Pin.OUT)

        voltage_raw = machine.ADC(machine.Pin(VOLTAGE_SENSOR_PIN)).read_u16()
        battery_voltage = round(voltage_raw * ADC_REFERENCE_VOLTAGE * VSYS_DIVIDER_RATIO / 65535, 3)
        rain_raw, rain_digital_wet = _read_rain_sensor(machine)
        wetness = _wetness(rain_raw)
        manual = bool(TURN_VALVE_ON_MANUALLY)

        now_s = _utc_now()
        if now_s is None:
            valve.value(1 if manual else 0)
            return {
                "success": manual,
                "platform": platform,
                "error": None if manual else "Clock not synced; valve kept closed.",
                "valve_open": manual,
                "manual_override": manual,
                "battery_voltage": battery_voltage,
                "rain_wetness": wetness,
                "rain_digital_wet": rain_digital_wet,
            }

        threshold = RAIN_THRESHOLD_LAST_12H
        result = _evaluate(
            _get_state(),
            now_s,
            wetness,
            _parse_start_time(VALVE_START_TIME),
            float(VALVE_RUN_DURATION_MINUTES),
            threshold,
        )

        valve_open = manual or result["valve_open"]
        valve.value(1 if valve_open else 0)
        rain_indicator.value(1 if result["rain_threshold_exceeded"] else 0)
        not_run_indicator.value(1 if result["valve_not_run_today"] else 0)

        local_s = now_s + _utc_offset_seconds(now_s)
        return {
            "success": True,
            "platform": platform,
            "now_utc": _iso(now_s),
            "local_time": "%02d:%02d" % ((local_s % 86400) // 3600, (local_s % 3600) // 60),
            "valve_open": valve_open,
            "manual_override": manual,
            "scheduled_open": result["valve_open"],
            "valve_start_time": VALVE_START_TIME,
            "valve_run_duration_minutes": VALVE_RUN_DURATION_MINUTES,
            "current_window_start_utc": _iso(result["current_window_start"]),
            "next_window_start_utc": _iso(result["next_window_start"]),
            "battery_voltage": battery_voltage,
            "rain_wetness": wetness,
            "rain_digital_wet": rain_digital_wet,
            "rain_peak_12h": result["rain_peak_12h"],
            "rain_threshold": threshold,
            "rain_threshold_exceeded": result["rain_threshold_exceeded"],
            "rain_clear_at_utc": _iso(result["rain_clear_at"]),
            "valve_not_run_today": result["valve_not_run_today"],
        }
    except Exception as e:
        if valve is not None:
            try:
                valve.value(0)
            except Exception:
                pass
        return {
            "success": False,
            "platform": platform,
            "error": str(e),
        }