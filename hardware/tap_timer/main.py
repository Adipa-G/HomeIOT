import sys
import time

# --- PIN CONFIGURATION ---
VOLTAGE_SENSOR_PIN = 26
VALVE_CONTROL_PIN = 0
RAIN_SENSOR_ACTIVATION_PIN = 1
RAIN_ANALOG_SENSOR_PIN = 27
RAIN_DIGITAL_SENSOR_PIN = 2
RUNNING_INDICATOR_PIN = 22
RAIN_THRESHOLD_EXCEEDED_INDICATOR_PIN = 21

# Fixed AEST; the valve runs an hour later by the clock during daylight saving.
UTC_OFFSET_HOURS = 10

# --- OVERRIDABLE SETTINGS ---
# Module variables are injected before this source runs, so only fall back to
# the defaults when the variable hasn't been configured.
if "VALVE_START_TIME" not in globals():
    VALVE_START_TIME = "17:00"
if "VALVE_RUN_DURATION_MINUTES" not in globals():
    VALVE_RUN_DURATION_MINUTES = 10
if "RAIN_THRESHOLD" not in globals():
    RAIN_THRESHOLD = 100
if "TURN_VALVE_ON_MANUALLY" not in globals():
    TURN_VALVE_ON_MANUALLY = False


def run(ctx):
    if sys.platform != "rp2":
        return {"success": False, "error": "Module not supported on platform: " + sys.platform}

    import machine

    Pin = machine.Pin
    valve = Pin(VALVE_CONTROL_PIN, Pin.OUT)
    power = Pin(RAIN_SENSOR_ACTIVATION_PIN, Pin.OUT)
    running = Pin(RUNNING_INDICATOR_PIN, Pin.OUT)
    running.value(1)
    try:
        # Power the rain sensor only while reading it so the probe doesn't corrode.
        power.value(1)
        time.sleep(1)
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

        # The valve pin remembers the last decision between runs: once open it
        # stays open for the window even if rain starts.
        scheduled = in_window and (valve.value() == 1 or not raining)

        valve_open = bool(TURN_VALVE_ON_MANUALLY) or scheduled
        valve.value(1 if valve_open else 0)
        Pin(RAIN_THRESHOLD_EXCEEDED_INDICATOR_PIN, Pin.OUT).value(1 if raining else 0)

        return {
            "success": True,
            "local_time": "%02d:%02d" % (t[3], t[4]) if synced else None,
            "valve_open": 24 if valve_open else 0,
            "manual_override": 24 if TURN_VALVE_ON_MANUALLY else 0,
            "rain_wetness": wetness,
            "rain_digital_wet": rain_digital_wet,
            "rain_threshold_exceeded": raining,
            # GPIO 26 sees VSYS / 2, so scale by 2 * 3.3 V.
            "battery_voltage": round(machine.ADC(VOLTAGE_SENSOR_PIN).read_u16() * 6.6 / 65535, 3),
        }
    except Exception as e:
        power.value(0)
        valve.value(0)
        return {"success": False, "error": str(e)}
    finally:
        running.value(0)