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

# Fixed AEST; the valve runs an hour later by the clock during daylight saving.
UTC_OFFSET_HOURS = 10

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
    RAIN_THRESHOLD
except NameError:
    RAIN_THRESHOLD = 100
try:
    TURN_VALVE_ON_MANUALLY
except NameError:
    TURN_VALVE_ON_MANUALLY = False


def run(ctx):
    if sys.platform != "rp2":
        return {"success": False, "error": "Module not supported on platform: " + sys.platform}

    import machine

    Pin = machine.Pin
    valve = Pin(VALVE_CONTROL_PIN, Pin.OUT)
    power = Pin(RAIN_SENSOR_ACTIVATION_PIN, Pin.OUT)
    try:
        # Power the rain sensor only while reading it so the probe doesn't corrode.
        power.value(1)
        time.sleep(0.1)
        rain_raw = machine.ADC(RAIN_ANALOG_SENSOR_PIN).read_u16()
        rain_digital_wet = Pin(RAIN_DIGITAL_SENSOR_PIN, Pin.IN, Pin.PULL_UP).value() == 0
        power.value(0)

        # Sensor output drops as it gets wetter: 0 = dry, 1023 = soaked.
        wetness = (65535 - rain_raw) * 1023 // 65535
        raining = wetness > RAIN_THRESHOLD

        t = time.gmtime(time.time() + UTC_OFFSET_HOURS * 3600)
        synced = t[0] >= 2024
        hour, minute = VALVE_START_TIME.split(":")
        start = int(hour) * 60 + int(minute)
        since_start = (t[3] * 60 + t[4] - start) % 1440
        in_window = synced and since_start < VALVE_RUN_DURATION_MINUTES

        # The output pins remember the last decision between runs: once the valve
        # is open it stays open for the window even if rain starts, and a skipped
        # window stays flagged until midnight.
        not_run_pin = Pin(VALVE_NOT_RUN_TODAY_INDICATOR_PIN, Pin.OUT)
        scheduled = in_window and (valve.value() == 1 or not raining)
        if in_window:
            not_run_today = not scheduled
        else:
            not_run_today = synced and not_run_pin.value() == 1 and since_start < 1440 - start

        valve_open = bool(TURN_VALVE_ON_MANUALLY) or scheduled
        valve.value(1 if valve_open else 0)
        not_run_pin.value(1 if not_run_today else 0)
        Pin(RAIN_THRESHOLD_EXCEEDED_INDICATOR_PIN, Pin.OUT).value(1 if raining else 0)

        return {
            "success": True,
            "local_time": "%02d:%02d" % (t[3], t[4]) if synced else None,
            "valve_open": 1 if valve_open else 0,
            "manual_override": 1 if TURN_VALVE_ON_MANUALLY else 0,
            "rain_wetness": wetness,
            "rain_digital_wet": rain_digital_wet,
            "rain_threshold_exceeded": raining,
            "valve_not_run_today": not_run_today,
            # GPIO 26 sees VSYS / 2, so scale by 2 * 3.3 V.
            "battery_voltage": round(machine.ADC(VOLTAGE_SENSOR_PIN).read_u16() * 6.6 / 65535, 3),
        }
    except Exception as e:
        power.value(0)
        valve.value(0)
        return {"success": False, "error": str(e)}